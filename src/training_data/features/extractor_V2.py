import time

from datetime import timezone, timedelta
from github import Github
from github.PullRequest import PullRequest

from db.db import PrReviewers, Session, PullRequest as db_PR, PrText, PrCode, PrAuthor, PrProject
from features.config import MAX_TRAINING_PR_AGE, DATETIME_NOW
from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features
from features.features_text import text_features

DATASET_AGE_WINDOW = timedelta(days=MAX_TRAINING_PR_AGE)

class Extractor:
    def __init__(self, api: Github, repo: str):
        self.api = api
        self.repo = repo

    def extract_features(self) -> None:
        self.run_seq()

    def run_seq(self):
        # Clean up feature DB tables
        closed_pulls = list(self.api.get_repo(full_name_or_id=self.repo).get_pulls(state='closed'))
        self.db_sync_and_clean(closed_pulls)

        # DATASET CUT-OFF (too old/long-running -> exclude from DATASET)
        if MAX_TRAINING_PR_AGE > 0:
            cutoff = DATETIME_NOW - DATASET_AGE_WINDOW
            closed_pulls = [pr for pr in closed_pulls if pr.created_at.replace(tzinfo=timezone.utc) >= cutoff]

        # Calc missing features
        author_features(self.api, closed_pulls)
        
        reviewer_features(self.api, closed_pulls)
        project_features(closed_pulls)
        text_features(closed_pulls)
        code_features(closed_pulls)
        

    def db_sync_and_clean(self, prs: list[PullRequest]):
        start_time = time.time()

        # Clean data to always recalculate
        # prs_nums = [pr.number for pr in prs]
        # with Session() as session:
        #     session.query(PrText).delete()
        #     session.query(PrProject).delete()
        #     session.query(PrCode).delete()
        #     session.query(PrReviewers).delete()
        #     session.query(PrAuthor).delete()
        #     session.commit()

        # TODO Review Sync for DB reuse
        save_prs_to_db_batched(prs)
        # save_prs_to_db_batched(prs)

        print(f"Step: \"DB Sync & Clean\" executed in {time.time() - start_time}s")

def save_prs_to_db_batched(prs: list[PullRequest]):
    batch_size = 100
    pr_batch = []

    for pr in prs:
        pr_batch.append(create_pr_obj(pr))

        if len(pr_batch) == batch_size:
            save_batch_to_db(pr_batch)
            pr_batch.clear()

    if len(pr_batch) > 0:
        save_batch_to_db(pr_batch)
        pr_batch.clear()
        
    # PRs Total
    with Session() as session:
        total = session.query(db_PR).count()
        print(f"A total of {total} PRs were saved")


def save_prs_to_db(prs: list[PullRequest]):
    db_PRs = [create_pr_obj(pr) for pr in prs]
    save_batch_to_db(db_PRs)


def save_batch_to_db(pr_batch: list[db_PR]):
    with Session() as session:
        session.add_all(pr_batch)
        session.commit()
        print(f"\t{len(pr_batch)} PRs were saved")


def create_pr_obj(pr: PullRequest) -> db_PR:
    return db_PR(
        number=pr.number,
        title=pr.title,
        state=pr.state,
        merged=pr.merged,
        author=pr.user.login,
        created_at=pr.created_at,
        closed_at=pr.closed_at,
        last_change=pr.updated_at
    )
