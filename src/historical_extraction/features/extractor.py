import re
import time
import json
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

    def extract_features(self, repo_name: str, hist_mode: bool = False) -> None:
        
        pr_status = 'closed' if hist_mode else 'open'

        self.run_seq(repo_name, pr_status)
        # self.run_parallel(repo_name, pr_status)


    def run_seq(self, repo_name: str, pr_status: str):
        # Fill DB with partial PR and Project objects
        db_init_PRs(self.api, repo_name, pr_status)

        # Extract project features
        # project_features(self.api, repo_name)

        # Extract code features
        # code_features(self.api, repo_name, pr_status)

        # Extract text features
        text_features(self.api, repo_name, pr_status)

        # Extract reviewer features
        # reviewer_features(self.api, repo_name, pr_status)

        # Extract author features
        # author_features(self.api, repo_name, pr_status)


    def run_parallel(self, repo_name: str, pr_status: str):
        # Fill DB with partial PR and Project objects
        init_pr = multiprocessing.Process(target=db_init_PRs, args=(self.api, repo_name, pr_status))

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

        init_pr.start()
        proj_feat.start()

        # Per PR features require all PR init before running to avoid errors
        init_pr.join()
        code_feat.start()
        text_feat.start()
        rev_feat.start()

        # Terminate finished processes
        rev_feat.join()
        author_feat.start()
        text_feat.join()
        code_feat.join()
        proj_feat.join()
        author_feat.join()


def db_init_PRs(api: Github, repo: str, pr_status: str) -> None:
    start_time = time.time()
    pull_requests = api.get_repo(full_name_or_id=repo).get_pulls(state=pr_status)

    db_users = []
    # Reset PRs table
    with Session() as session:
        db_users = session.query(db_User).all()
        session.query(db_PR).delete()
        session.commit()

        if len(db_users) > 0:
            start_id = max(user.id for user in db_users)
            db_users = {user.username:user for user in db_users}
        else:
            start_id = 0
            db_users = {}

    new_users = []
    db_prs = []

    for pr in pull_requests:
        pr_user = pr.user
        user = db_users.get(pr_user.login, None)

        if user is None:
            start_id += 1
            user = db_User(id=start_id, username=pr_user.login, tag='E')
            db_users[user.username] = user
            new_users.append(user)
            db_prs.append(db_PR(number=pr.number, title=pr.title, merged=pr.merged, author_id=start_id))
        else:
            db_prs.append(db_PR(number=pr.number, title=pr.title, merged=pr.merged, author_id=user.id))

    with Session() as session:
        session.add_all(new_users)
        session.add_all(db_prs)
        session.commit()

    print(f"PRs and new Users are initialized in {time.time() - start_time}s")
