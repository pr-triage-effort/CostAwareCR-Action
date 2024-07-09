import re
import time
from github import Github
from github.PullRequest import PullRequest
from features.features_project import project_features
from features.features_code import code_dir_features, code_file_features, code_modify_entropy
from features.features_reviewer import reviewer_counts, avg_reviewer_review_count, avg_reviewer_exp
from features.features_author import author_review_number, author_merge_ratios,  total_change_number, author_experience, author_changes_per_week

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
        print(f"Pr: {pr.title}")

        # Code features
        features.update(self.extract_reviewer_features(pr, review_counts))
        features.update(self.extract_author_features(pr))
        features.update(self.extract_project_features(pr))
        features.update(self.extract_text_features(pr))
        features.update(self.extract_code_features(pr))

        return features

    def extract_reviewer_features(self, pr: PullRequest, review_counts: dict) -> dict:
        feats = {}
        # start_time = time.time()

        # project = self.gApi.get_repo(full_name_or_id=self.repo)
        # Replace hardcoded value with function implementation

        feats.update(reviewer_counts(pr, self.gApi))
        # time1 = time.time()
        # print(f"\t\t reviewer_counts - {round(time1-start_time,3)}s")

        feats.update(avg_reviewer_review_count(pr, review_counts))
        # time2 = time.time()
        # print(f"\t\t avg_reviewer_review_count - {round(time2-time1,3)}s")

        feats.update(avg_reviewer_exp(pr))
        # time3 = time.time()
        # print(f"\t\t avg_reviewer_exp - {round(time3-time2,3)}s")

        return feats

    def extract_author_features(self, pr: PullRequest) -> dict:
        feats = {}
        start_time = time.time()
        
        # Replace hardcoded value with function implementation
        feats["author_experience"] = author_experience(pr, self.gApi, self.feature_cache)
        time1 = time.time()
        print(f"\t\t author_experience - {round(time1-start_time,3)}s")

        feats.update(author_merge_ratios(pr, self.gApi, self.feature_cache))
        time2 = time.time()
        print(f"\t\t author_merge_ratios - {round(time2-time1,3)}s")

        feats["total_change_number"] = total_change_number(pr, self.gApi, self.feature_cache)
        time3 = time.time()
        print(f"\t\t total_change_number - {round(time3-time2,3)}s")

        feats["author_review_number"] = author_review_number(pr, self.gApi, self.feature_cache)
        time4 = time.time()
        print(f"\t\t author_review_number - {round(time4-time3,3)}s")

        feats["author_changes_per_week"] = author_changes_per_week(pr, self.gApi, self.feature_cache)
        time5 = time.time()
        print(f"\t\t author_changes_per_week - {round(time5-time4,3)}s")

        return feats


    def extract_project_features(self, pr: PullRequest) -> dict:
        feats = {}
        # start_time = time.time()
        
        feats.update(project_features(pr, self.gApi, self.feature_cache))
        # time1 = time.time()
        # print(f"\t\t project_features - {round(time1-start_time,3)}s")

        return feats
    

    # TODO check how intricate parsing should be (regex)
    def extract_text_features(self, pr: PullRequest) -> dict:
        feats = {
            'description_length': 0,
            'is_documentation': 0,
            'is_bug_fixing': 0,
            'is_feature': 0
        }

        description = pr.body
        # print(description)

        # TODO check with client if the following gives a viable approximation
        feats['description_length'] = len(re.findall(r'\w+', description))

        # TODO Are doc/fix/feat mutually exclusive?
        # TODO Check if "doc" and others should be isolated words (word boundaries in regex)
        keywords = {'doc': 'doc', 'licence': 'doc', 'copyright': 'doc', 'bug': 'fix', 'fix': 'fix', 'defect': 'fix'}
        for key, value in keywords.items():
            if re.search(rf'\b{re.escape(key)}\b', description, re.IGNORECASE):
                match(value):
                    case 'doc':
                        feats["is_documentation"] = 1
                        return feats
                    case 'fix':
                        feats["is_bug_fixing"] = 1
                        return feats

        feats["is_feature"] = 1
        return feats

    def extract_code_features(self, pr: PullRequest) -> dict:
        feats = {}
        # start_time = time.time()

        # Replace hardcoded value with function implementation
        feats.update(code_dir_features(pr))
        # time1 = time.time()
        # print(f"\t\t code_dir_features - {round(time1-start_time,3)}s")
        
        feats.update(code_file_features(pr))
        # time2 = time.time()
        # print(f"\t\t code_file_features - {round(time2-time1,3)}s")

        feats.update(code_modify_entropy(pr))
        # time3 = time.time()
        # print(f"\t\t code_modify_entropy - {round(time3-time2,3)}s")

        return feats
    