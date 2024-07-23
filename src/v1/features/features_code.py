import math
from scipy.stats import entropy
from github.PullRequest import PullRequest

def code_features(pr: PullRequest):
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
    modify_entropy = entropy(entropy_pks, base=2)

    return {
            'modified_directories': modified_directories,
            'modify_entropy': modify_entropy,
            'lines_added': lines_added,
            'lines_deleted': lines_deleted,
            'files_modified': files_modified,
            'files_added': files_added,
            'files_deleted': files_deleted,
            'subsystem_num': subsystem_num,
        }
