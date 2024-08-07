import time
import multiprocessing as mp
from datetime import timezone, timedelta
from math import ceil

from github import Github
from github.PullRequest import PullRequest
from sqlalchemy import func

from db.db import PrReviewers, Session, PullRequest as db_PR, PrText, PrCode, PrAuthor
from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features
from features.features_text import text_features

POOL_MAX_PROCESSES = 4

class Extractor:
    def __init__(self, api: Github, repo: str):
        self.api = api
        self.repo = repo
        self.feature_cache = {}
        self.open_prs = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='open'))
        self.closed_prs = []

    def extract_features(self) -> None:
        self.run_parallel()

    def run_parallel(self):
        pull_requests = [pr for pr in self.open_prs if not pr.draft]

        db_cleanup(pull_requests)
        refetch = db_pr_state_refresh(self.api, self.repo, pull_requests)

        if refetch:
           self.open_prs = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='open'))
           pull_requests = [pr for pr in self.open_prs if not pr.draft]

        proj_feat = mp.Process(target=project_features, args=(self.repo,))
        text_feat = mp.Process(target=text_features, args=(pull_requests,))
        code_feat = mp.Process(target=code_features, args=(pull_requests,))
        rev_feat = mp.Process(target=reviewer_features, args=(self.api, pull_requests))
        author_feat = mp.Process(target=author_features, args=(self.api, pull_requests))

        proj_feat.start()
        code_feat.start()
        text_feat.start()
        rev_feat.start()
        author_feat.start()

        # Terminate finished processes
        text_feat.join()
        code_feat.join()
        proj_feat.join()
        rev_feat.join()
        author_feat.join()

    def run_seq(self):
        pull_requests = [pr for pr in self.open_prs if not pr.draft]

        db_cleanup(pull_requests)
        db_pr_state_refresh(self.api, self.repo, pull_requests)
        project_features(self.api, self.repo)
        text_features(pull_requests)
        code_features(pull_requests)
        reviewer_features(self.api, pull_requests)
        author_features(self.api, pull_requests)



def db_cleanup(prs: list[PullRequest]):
    start_time = time.time()
    prs_nums = [pr.number for pr in prs]

    # Clear feature tables that must always be recalculated
    with Session() as session:
        session.query(PrText).delete()
        session.query(PrReviewers).delete()
        session.query(PrCode).filter(~PrCode.pr_num.in_(prs_nums)).delete(synchronize_session='fetch')
        session.query(PrAuthor).filter(~PrAuthor.pr_num.in_(prs_nums)).delete(synchronize_session='fetch')
        session.commit()

    print(f"Step: \"DB Cleanup\" executed in {time.time() - start_time}s")

def db_pr_state_refresh(api: Github, repo: str, open_prs: list[PullRequest]) -> bool:
    start_time = time.time()
    initial_upload = False

    with Session() as session:
        last_update = session.query(func.max(db_PR.last_update)).scalar() or None

        # Bulk insert of data
        if last_update is None:
            initial_save_open_prs(open_prs)
            initial_save_closed_prs(api, repo)
            last_update = session.query(func.max(db_PR.last_update)).scalar()
            initial_upload = True

        # Perform updates only
        last_update = last_update.replace(tzinfo=timezone.utc)
        updated_pulls = list(api.get_repo(repo).get_pulls(state='all', sort='updated', direction='desc'))

        for pr in updated_pulls:
            if pr.updated_at < last_update - timedelta(days=1):
                break

            pr_data = session.query(db_PR).filter_by(number=pr.number).first()
            if pr_data:
                pr_data.title = pr.title
                pr_data.state = pr.state
                pr_data.merged = pr.merged
                pr_data.author = pr.user.login
                pr_data.created = pr.created_at
                pr_data.closed = pr.closed_at
            else:
                if pr.state == 'open' and pr.draft:
                    continue
                else:
                    new_pr = db_PR(
                        number=pr.number,
                        title=pr.title,
                        state=pr.state,
                        merged=pr.merged,
                        author=pr.user.login,
                        created=pr.created_at,
                        closed=pr.closed_at,
                    )
                    session.add(new_pr)

        session.commit()

    print(f"Step: \"DB PR refresh\" executed in {time.time() - start_time}s")
    return initial_upload

def initial_save_open_prs(open_prs: list[PullRequest]):
    start = time.time()
    num_prs = len(open_prs)
    batch_size = ceil(num_prs / POOL_MAX_PROCESSES)

    # Parallel processing
    pool = mp.Pool(processes=POOL_MAX_PROCESSES)
    manager = mp.Manager()
    db_prs = manager.list()

    def collect_result(result):
        db_prs.extend(result)

    for i in range(0, len(open_prs), batch_size):
        pr_batch = open_prs[i:i + batch_size]
        pool.apply_async(db_create_batch, (pr_batch,), callback=collect_result)

    pool.close()
    pool.join()

    with Session() as session:
        if db_prs:
            session.add_all(db_prs)
            session.commit()

    print(f"\t{num_prs} Open PRs processed in {time.time() - start}s")


def initial_save_closed_prs(api: Github, repo: str):
    start = time.time()
    closed_prs = list(api.get_repo(repo).get_pulls(state='closed', sort='created', direction='desc'))
    num_prs = len(closed_prs)
    batch_size = ceil(num_prs / POOL_MAX_PROCESSES)

    # Parallel processing
    pool = mp.Pool(processes=POOL_MAX_PROCESSES)
    manager = mp.Manager()
    db_prs = manager.list()

    def collect_result(result):
        db_prs.extend(result)

    for i in range(0, len(closed_prs), batch_size):
        pr_batch = closed_prs[i:i + batch_size]
        pool.apply_async(db_create_batch, (pr_batch,), callback=collect_result)

    pool.close()
    pool.join()

    with Session() as session:
        if db_prs:
            session.add_all(db_prs)
            session.commit()

    print(f"\t{num_prs} Closed PRs processed in {time.time() - start}s")

def db_create_batch(pr_batch: list[PullRequest]):
    return [db_PR(number=pr.number, title=pr.title, state=pr.state, merged=pr.merged, author=pr.user.login, created=pr.created_at, closed=pr.closed_at) for pr in pr_batch]
