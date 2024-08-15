import time
import multiprocessing as mp
import numpy as np
from datetime import timezone, timedelta, datetime
from math import ceil
from typing import List

from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository
from sqlalchemy import func

from db.db import PrReviewers, Session, PullRequest as db_PR, PrText, PrCode, PrAuthor
from features.config import LOAD_PROCESSES, LOAD_PAGES, LOAD_PRS
from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features
from features.features_text import text_features

class Extractor:
    def __init__(self, api: Github, repo: str):
        self.api = api
        self.repo = repo

    def extract_features(self) -> None:
        # self.run_parallel()
        self.run_seq()

    def run_seq(self):
        # Sync PR states with project
        self.db_pr_state_refresh()

        # Clean up feature DB tables
        pull_requests = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='open'))
        pull_requests = [pr for pr in pull_requests if not pr.draft]
        self.db_cleanup(pull_requests)

        # Calc missing features
        project_features(self.repo)
        text_features(pull_requests)
        code_features(pull_requests)
        reviewer_features(self.api, pull_requests)
        author_features(self.api, pull_requests)

    def run_parallel(self):
        # Sync PR states with project
        self.db_pr_state_refresh()

        # Clean up feature DB tables
        pull_requests = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='open'))
        pull_requests = [pr for pr in pull_requests if not pr.draft]
        self.db_cleanup(pull_requests)

        proj_feat = mp.Process(target=project_features, args=(self.repo,))
        text_feat = mp.Process(target=text_features, args=(pull_requests,))
        code_feat = mp.Process(target=code_features, args=(pull_requests,))
        rev_feat = mp.Process(target=reviewer_features, args=(self.api, pull_requests))
        author_feat = mp.Process(target=author_features, args=(self.api, pull_requests))

        rev_feat.start()
        code_feat.start()
        proj_feat.start()
        text_feat.start()

        # Terminate finished processes
        rev_feat.join()
        author_feat.start()
        code_feat.join()
        text_feat.join()
        proj_feat.join()
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

    def db_pr_state_refresh(self):
        start_time = time.time()
        repo = self.api.get_repo(self.repo)
        latest_updated = repo.get_pulls(state='all', sort='updated', direction='desc')

        with Session() as session:
            last_update = session.query(func.max(db_PR.last_update)).scalar() or None

        # Bulk insert of data (DB empty)
        if last_update is None:
            initial_save_prs(repo, 'open')
            initial_save_prs(repo, 'closed')
            last_update = session.query(func.max(db_PR.last_update)).scalar()

        with Session() as session:
            # Perform updates only
            last_update = last_update.replace(tzinfo=timezone.utc)
            for pr in latest_updated:
                since_step_start = datetime.now(timezone.utc) - datetime.fromtimestamp(start_time, timezone.utc)
                if pr.updated_at < (last_update - timedelta(seconds=since_step_start.seconds)):
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
                        new_pr = create_pr_obj(pr)
                        session.add(new_pr)

            session.commit()
        print(f"Step: \"DB PR refresh\" executed in {time.time() - start_time}s")


def initial_save_prs(repo: Repository, pr_status: str):
    print(f"\tBeginning filling DB with {pr_status} PRs")
    start = time.time()

    # Get all PR refs and optionally filter drafts
    prs = fetch_all_pr_pages(repo, pr_status)

    if pr_status == 'open':
        prs = [pr for pr in prs if not pr.draft]

    pool = mp.Pool(processes=LOAD_PROCESSES)
    batch_size = LOAD_PRS

    def collect_result(result):
        if result:
            with Session() as session:
                session.add_all(result)
                session.commit()
            print(f"\t\t{len(result)} {pr_status} PRs saved in {time.time() - start}s")

    for j in range(0, len(prs), batch_size):
        pr_batch = prs[j:j + batch_size]
        pool.apply_async(db_create_pr_batch, (pr_batch,), callback=collect_result)

    pool.close()
    pool.join()
    print(f"\tDB filled with {pr_status} PRs in {time.time() - start}s")

def fetch_all_pr_pages(repo: Repository, pr_status: str) -> list[PullRequest]:
    start = time.time()
    total_prs = repo.get_pulls(state=pr_status).totalCount
    total_pages = ceil(total_prs / repo._requester.per_page)
    pages_per_proc = ceil(total_pages/LOAD_PROCESSES)

    pool = mp.Pool(processes=LOAD_PROCESSES)
    results = []

    # Fetch
    for j in range(0, total_pages, pages_per_proc):
        result = pool.apply_async(fetch_pr_pages, (repo, pr_status, pages_per_proc, j, total_pages))
        results.append(result)

    pool.close()
    pool.join()

    print(f"\t\tAll {pr_status} PR references fetched in {time.time() - start}s")

    # Aggregate
    prs = []
    for r in results:
        prs.extend(r.get())

    return prs

def fetch_pr_pages(repo: Repository, pr_status: str, pages_num: int, from_page: int, max_page: int) -> list[PullRequest]:
    prs = repo.get_pulls(state=pr_status, sort='created', direction='desc')

    results = []
    last_page = from_page + pages_num - 1

    while from_page <= max_page and from_page <= last_page:
        page = prs.get_page(from_page)
        results.extend(page)
        from_page += 1

    return results

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
