import os
import json
import time

from operator import itemgetter
from dotenv import load_dotenv
from github import Github, Auth, GithubRetry
from sqlalchemy.orm import Session

from db.db import Session, init_db, Project, PullRequest
from features.extractor import Extractor
from utils import time_exec

def main():
    start_time = time.time()

    # Extract Env vars
    load_dotenv(override=True)
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")


    # APIs
    auth = Auth.Token(token)
    retry = GithubRetry(backoff_factor=.25)
    github_api = Github(auth=auth, retry=retry)

    # Modules
    extractor = Extractor(github_api, repo)

    #DB
    init_db()

    step_time = time_exec(start_time, "Init")

    # Extract Features
    extractor.extract_features(repo_name=repo)

    step_time = time_exec(step_time, "Feature extract")

    # Dump features to json
    features = build_feature_dataset(repo)
    write_to_json(features, "./features.json")


def write_to_json(data: list, path: str):
    with open(path, "w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2)

def build_feature_dataset(repo: str):
    start_time = time.time()

    with Session() as session:
        project = session.query(Project).where(Project.name == repo).one()
        prs = session.query(PullRequest).all()
        features = [build_pr_features(pr, project) for pr in prs]

    print(f"Dataset generation done in {time.time() - start_time}s")
    return features

def build_pr_features(pr: PullRequest, project: Project):
    author = pr.author
    reviewer_feat = pr.reviewer_feat
    text_feat = pr.text_feat
    code_feat = pr.code_feat

    return {
        'title': pr.title,
        'number': pr.number,
        'merged': False,
        'features': {
            "author_experience": author.experience,
            "total_change_num": author.total_change_number,
            "author_review_num": author.review_number,
            "author_changes_per_week": author.changes_per_week,
            "author_merge_ratio": author.global_merge_ratio,
            "author_merge_ratio_in_project": author.project_merge_ratio,
            "num_of_reviewers": reviewer_feat.humans,
            "num_of_bot_reviewers": reviewer_feat.bots,
            "avg_reviewer_experience": reviewer_feat.avg_experience,
            "avg_reviewer_review_count": reviewer_feat.avg_reviews,
            "project_changes_per_week": project.changes_per_week,
            "changes_per_author": project.changes_per_author,
            "project_merge_ratio": project.merge_ratio,
            "description_length": text_feat.description_len,
            "is_documentation": text_feat.is_documentation,
            "is_bug_fixing": text_feat.is_bug_fixing,
            "is_feature": text_feat.is_feature,
            "num_of_directory": code_feat.num_of_directory,
            "modify_entropy": code_feat.modify_entropy,
            "lines_added": code_feat.lines_added,
            "lines_deleted": code_feat.lines_deleted,
            "files_modified": code_feat.files_modified,
            "files_added": code_feat.files_added,
            "files_deleted": code_feat.files_deleted,
            "subsystem_num": code_feat.subsystem_num
        }
    }

if __name__ == "__main__": 
    main()
