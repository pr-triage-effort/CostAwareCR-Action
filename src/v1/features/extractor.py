import re
import time
import json

from github import Github
from github.PullRequest import PullRequest

from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features
from features.user_utils import is_bot_user

class Extractor:
    def __init__(self, gApi: Github, repo: str):
        self.gApi = gApi
        self.repo = repo
        
        # Cache
        self.feature_cache = {
            'users': {},
            'project': {}
        }         

    def set_cache(self, file_path: str):
        with open(file_path, encoding="utf-8") as cache:
            self.feature_cache = json.load(cache)

    def get_cache_(self) -> dict:
        return self.feature_cache

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

        print(f"\t ({self.feature_cache.get('users').get(pr.user.login, {}).get('type', None)}-user) Pr({nb}): {pr.title} | {round(time.time()-start_time,3)}s")

        return features

    def extract_reviewer_features(self, pr: PullRequest) -> dict:
        return reviewer_features(pr, self.gApi, self.feature_cache)

    def extract_author_features(self, pr: PullRequest) -> dict:
        return author_features(pr, self.gApi, self.feature_cache)

    def extract_project_features(self, pr: PullRequest) -> dict:
        return project_features(pr, self.gApi, self.feature_cache)

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
    