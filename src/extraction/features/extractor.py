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

class Extractor:
    def __init__(self, api: Github, repo: str, load_processes: int):
        self.api = api
        self.repo = repo
        self.db_processes = load_processes
        self.open_prs = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='open'))
        self.closed_prs = []

    def extract_features(self) -> None:
        # self.run_parallel()
        self.run_seq()

    def run_seq(self):
        pull_requests = [pr for pr in self.open_prs if not pr.draft]

        self.db_cleanup(pull_requests)
        refetch = self.db_pr_state_refresh(pull_requests)

        if refetch:
           self.open_prs = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='open'))
           pull_requests = [pr for pr in self.open_prs if not pr.draft]

        project_features(self.repo)
        text_features(pull_requests)
        code_features(pull_requests)
        reviewer_features(self.api, pull_requests)
        author_features(self.api, pull_requests)

    def run_parallel(self):
        pull_requests = [pr for pr in self.open_prs if not pr.draft]

        self.db_cleanup(pull_requests)
        refetch = self.db_pr_state_refresh(pull_requests)

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

        # Terminate finished processes
        text_feat.join()
        code_feat.join()
        proj_feat.join()
        rev_feat.join()
        author_feat.start()
        author_feat.join()

    def db_cleanup(self, prs: list[PullRequest]):
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

    def db_pr_state_refresh(self, open_prs: list[PullRequest]) -> bool:
        start_time = time.time()
        latest_updated_rs = list(self.api.get_repo(self.repo).get_pulls(state='all', sort='updated', direction='desc'))
        initial_upload = False

        with Session() as session:
            last_update = session.query(func.max(db_PR.last_update)).scalar() or None

        # Bulk insert of data (DB empty)
        if last_update is None:
            closed_prs = list(self.api.get_repo(self.repo).get_pulls(state='closed', sort='created', direction='desc'))
            initial_save_prs(open_prs, self.db_processes, 'Open')
            initial_save_prs(closed_prs, self.db_processes, 'Closed')
            initial_upload = True

        with Session() as session:
            if initial_upload:
                last_update = session.query(func.max(db_PR.last_update)).scalar()

            # Perform updates only
            last_update = last_update.replace(tzinfo=timezone.utc)
            for pr in latest_updated_rs:
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

def initial_save_prs(prs: list[PullRequest], process_num: int, pr_type: str):
    start = time.time()
    num_prs = len(prs)
    # batch_size = ceil(num_prs / process_num)
    batch_size = 100

    # Parallel processing
    pool = mp.Pool(processes=process_num)
    manager = mp.Manager()
    db_prs = manager.list()

    def collect_result(result):
        print(f"\t{len(result)} PRs saved in {time.time() - start}s")
        db_prs.extend(result)

    for i in range(0, len(prs), batch_size):
        pr_batch = prs[i:i + batch_size]
        pool.apply_async(db_create_pr_batch, (pr_batch,), callback=collect_result)

    pool.close()
    pool.join()

    with Session() as session:
        if db_prs:
            session.add_all(db_prs)
            session.commit()

    print(f"\t{num_prs} {pr_type} PRs processed in {time.time() - start}s")

def db_create_pr_batch(pr_batch: list[PullRequest]):
    return [create_pr_obj(pr) for pr in pr_batch]

def create_pr_obj(pr: PullRequest) -> db_PR:
    return db_PR(
        number=pr.number,
        title=pr.title,
        state=pr.state,
        merged=pr.merged,
        author=pr.user.login,
        created=pr.created_at,
        closed=pr.closed_at
    )
