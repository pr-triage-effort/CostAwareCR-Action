import re
import time
import json

from github import Github
from github.PullRequest import PullRequest
from db.db import Session, db_get_user

from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features
from features.user_utils import is_bot_user

class Extractor:
    def __init__(self, gApi: Github, repo: str):
        self.gApi = gApi
        self.repo = repo
        self.feature_cache = {}

    def extract_features(self, pr: PullRequest, nb: int) -> dict:
        features = {}
        # print(f"Pr: {pr.title}")
        start_time = time.time()

        # Code features
        features.update(self.extract_author_features(pr))
        # print(f'\t\tAuthor features extracted at: {round(time.time()-start_time,3)}s')
        features.update(self.extract_reviewer_features(pr))
        # print(f'\t\tReviewer features extracted at: {round(time.time()-start_time,3)}s')
        features.update(self.extract_project_features(pr))
        # print(f'\t\tProject features extracted at: {round(time.time()-start_time,3)}s')
        features.update(self.extract_text_features(pr))
        # print(f'\t\tText features extracted at: {round(time.time()-start_time,3)}s')
        features.update(self.extract_code_features(pr))
        # print(f'\t\tCode features extracted at: {round(time.time()-start_time,3)}s')

        with Session() as session:
            user = db_get_user(pr.user.login, session)
            print(f"\t ({user.type}-user) Pr({nb}): {pr.title} | {round(time.time()-start_time,3)}s")

        return features

    def extract_reviewer_features(self, pr: PullRequest) -> dict:
        return reviewer_features(pr, self.gApi, self.feature_cache)

    def extract_author_features(self, pr: PullRequest) -> dict:
        return author_features(pr, self.gApi, self.feature_cache)

    def extract_project_features(self, pr: PullRequest) -> dict:
        return project_features(pr, self.gApi)

    def extract_text_features(self, pr: PullRequest) -> dict:
        feats = {
            'description_length': 0,
            'is_documentation': 0,
            'is_bug_fixing': 0,
            'is_feature': 0
        }

        description = pr.body

        if description is not None:
            feats['description_length'] = len(re.findall(r'\w+', description))

            # TODO play with regex to include more keywords
            keywords = ['doc, license, copyright, bug, fix, defect']
            for word in keywords:
                if re.search(rf'\b{re.escape(word)}\b', description, re.IGNORECASE):
                    match(word):
                        case 'doc'|'license'|'copyright':
                            feats["is_documentation"] = 1
                            return feats
                        case 'bug'|'fix'|'defect':
                            feats["is_bug_fixing"] = 1
                            return feats

        feats["is_feature"] = 1
        return feats

    def extract_code_features(self, pr: PullRequest) -> dict:
        return code_features(pr)
    