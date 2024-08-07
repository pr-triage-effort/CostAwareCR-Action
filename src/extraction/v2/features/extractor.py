import time
import multiprocessing

from github import Github
from github.PullRequest import PullRequest
from db.db import Session, PullRequest as db_PR, User as db_User

from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features
from features.features_text import text_features
from features.user_utils import is_bot_user

from features.config import HISTORY_RANGE_DAYS, HISTORY_LIMIT

class Extractor:
    def __init__(self, api: Github, repo: str):
        self.api = api
        self.repo = repo
        self.feature_cache = {}

    def extract_features(self, repo_name: str) -> None:
        pr_status = 'open'
        self.run_parallel(repo_name, pr_status)

    def run_parallel(self, repo_name: str, pr_status: str):
        pull_requests = list(self.api.get_repo(full_name_or_id=repo_name).get_pulls(state=pr_status))

        # Fill DB with partial User objects
        init_users = multiprocessing.Process(target=db_init_new_users, args=(pull_requests,))

        # Fill DB with partial PR objects
        init_prs = multiprocessing.Process(target=db_init_PRs, args=(pull_requests,))

        # Extract project features
        proj_feat = multiprocessing.Process(target=project_features, args=(self.api, repo_name))

        # Extract text features
        text_feat = multiprocessing.Process(target=text_features, args=(self.api, repo_name, pr_status))

        # Extract code features
        code_feat = multiprocessing.Process(target=code_features, args=(self.api, repo_name, pr_status))

        # Extract reviewer features
        rev_feat = multiprocessing.Process(target=reviewer_features, args=(self.api, repo_name, pr_status))

        # Extract reviewer features
        author_feat = multiprocessing.Process(target=author_features, args=(self.api, repo_name, pr_status))

        proj_feat.start()
        init_users.start()
        code_feat.start()
        text_feat.start()
        init_users.join()
        init_prs.start()
        rev_feat.start()
        rev_feat.join()
        author_feat.start()
        
        # Terminate finished processes
        text_feat.join()
        init_prs.join()
        code_feat.join()
        proj_feat.join()
        author_feat.join()


def db_init_new_users(prs: list[PullRequest]):
    start_time = time.time()

    with Session() as session:
        db_users = session.query(db_User).all()

    db_users = {user.username:user for user in db_users}
    new_users = list(dict.fromkeys([pr.user.login for pr in prs if pr.user.login not in db_users.keys()]))
    new_users = [db_User(username=username, tag='E') for username in new_users]

    if len(new_users) > 0:
        with Session() as session:
            session.add_all(new_users)
            session.commit()

    print(f"New Users added to db in {time.time() - start_time}s")


def db_init_PRs(prs: list[PullRequest]) -> None:
    start_time = time.time()

    # Reset PRs table
    with Session() as session:
        session.query(db_PR).delete()
        session.commit()
        db_users = session.query(db_User).all()

    db_users = {user.username: user for user in db_users}
    db_prs = [db_PR(number=pr.number, title=pr.title, merged=pr.merged, author_id=db_users.get(pr.user.login).id) for pr in prs]

    with Session() as session:
        session.add_all(db_prs)
        session.commit()

    print(f"PRs and new Users are initialized in {time.time() - start_time}s")
