import os
import json
import time

from operator import itemgetter
from dotenv import load_dotenv
from github import Github, Auth, GithubRetry

from db.db import Session, init_db
from features.extractor import Extractor
# from ml_model.analyzer import Analyzer
from utils import time_exec

def analysis_script():
    start_time = time.time()

    # Extract Env vars
    load_dotenv(override=True)
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")
    cache_reset = os.environ.get("RESET_CACHE")


    # APIs
    auth = Auth.Token(token)
    retry = GithubRetry(backoff_factor=.25)
    github_api = Github(auth=auth, retry=retry)

    # Modules
    extractor = Extractor(github_api, repo)

    #DB
    init_db(cache_reset == 'true')

    step_time = time_exec(start_time, "Init")


    # Extract Features
    features = []
    analysis_cnt = 1

    pull_requests = github_api.get_repo(full_name_or_id=repo).get_pulls(state="open")
    for pull in pull_requests:
        pr_feats = extractor.extract_features(pull, analysis_cnt)
        features.append(pr_feats)
        analysis_cnt += 1

    step_time = time_exec(step_time, "Feature extract")

    # Dump features to json
    # list = [key['features'] for key in features]
    write_to_json(features, "./features.json")


def write_to_json(data: list, path: str):
    with open(path, "w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2)


analysis_script()
