import time

from scipy.stats import entropy
from github import Github
from github.PullRequest import PullRequest

from db.db import Session, PrCode

def code_features(api: Github, repo: str, pr_status: str):
    start_time = time.time()

    # Reset PrCode table
    with Session() as session:
        session.query(PrCode).delete()
        session.commit()

    pull_requests = api.get_repo(full_name_or_id=repo).get_pulls(state=pr_status)
    code_feats = [extract_code_feature(pr) for pr in pull_requests]

    with Session() as session:
        session.add_all(code_feats)
        session.commit()

    print(f"Step: \"Code Features\" executed in {time.time() - start_time}s")


def extract_code_feature(pr: PullRequest) -> PrCode:
    # Features
    modified_directories = 0
    modify_entropy = 0
    lines_added = pr.additions
    lines_deleted = pr.deletions
    files_modified = 0
    files_added = 0
    files_deleted = 0
    subsystem_num = 0

    # Temp vars
    top_dir_changed = []
    bot_dir_changes = []
    entropy_pks = []
    total_modified_lines = lines_added + lines_deleted



    # Scan changed files
    for file in pr.get_files():
        # Modified directories/subsystems
        file_path = file.filename
        split_path = file_path.split("/")

        if len(split_path) > 1:
            top = split_path[0]
            bottom = file_path.rsplit('/', 1)[0]

            if top_dir_changed.count(top) == 0:
                top_dir_changed.append(top)

            if bot_dir_changes.count(bottom) == 0:
                bot_dir_changes.append(bottom)

        # PK ratio for entropy
        if total_modified_lines > 0 and file.changes > 0:
            file_pk = file.changes / total_modified_lines
            entropy_pks.append(file_pk)

        # File changes
        match file.status:
            case "added":
                files_added += 1
            case "removed":
                files_deleted += 1
            # TODO Check definition of 'modified' with client
            case "modified" | "renamed" | "changed":
                files_modified += 1

    # Feature calc:
    modified_directories = len(bot_dir_changes)
    subsystem_num = len(top_dir_changed)
    modify_entropy = entropy(entropy_pks, base=2) if len(entropy_pks) > 0 else 0

    feats = PrCode(
        num_of_directory = modified_directories,
        modify_entropy = modify_entropy,
        lines_added = lines_added,
        lines_deleted = lines_deleted,
        files_added = files_added,
        files_deleted = files_deleted,
        files_modified = files_modified,
        subsystem_num = subsystem_num,
        pr_num = pr.number
    )

    return feats