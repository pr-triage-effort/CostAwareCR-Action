import re
import time
from github import Github
from github.PullRequest import PullRequest
from features.features_project import project_features
from features.features_code import code_features
from features.features_reviewer import reviewer_features
from features.features_author import  author_features

class Extractor:
    def __init__(self, gApi: Github, repo: str):
        self.gApi = gApi
        self.repo = repo
        self.init_shared_deps()
        self.feature_cache = {
            'users': {},
            'project': {}
        }

    def init_shared_deps(self):
        # All repo closed PRS
        # All repo opened PRS
        # All repo merged PRS
        pass

    def extract_features(self, pr: PullRequest, review_counts: dict) -> dict:
        features = {}
        # print(f"Pr: {pr.title}")
        start_time = time.time()

        # Code features
        features.update(self.extract_author_features(pr))
        features.update(self.extract_reviewer_features(pr))
        features.update(self.extract_project_features(pr))
        features.update(self.extract_text_features(pr))
        features.update(self.extract_code_features(pr))

        print(f"\t Pr: {pr.title} | {round(time.time()-start_time,3)}s")

        return features

    def extract_reviewer_features(self, pr: PullRequest) -> dict:
        feats = {}

        return reviewer_features(pr, self.gApi, self.feature_cache)

        # feats.update(reviewer_counts(pr, self.gApi))
        # feats.update(avg_reviewer_review_count(pr, review_counts))
        # feats.update(avg_reviewer_exp(pr))

        return feats

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
    