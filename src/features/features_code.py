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

        # File changes
        match file.status:
            case "added":
                files_added += 1
            case "removed":
                files_deleted += 1
            # TODO Check validity with client
            case "modified" | "renamed" | "changed":
                files_modified += 1
                # PK ratio for entropy
                file_pk = file.changes / total_modified_lines
                entropy_pks.append(file_pk)

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


# TODO Validate the calculation
def code_modify_entropy(pr: PullRequest) -> dict:
    entropy = 0
    tot_line_mod = pr.additions + pr.deletions

    for file in pr.get_files():
        if file.status in ["modified", "renamed" "changed"]:
            line_mod = file.changes
            pk = line_mod / tot_line_mod
            ent_change = pk * math.log2(pk)
            entropy += ent_change
            # print(f"ent_change = {ent_change}")

    if entropy != 0:
        entropy *= -1

    # print(f"PR: {pr.title} | mod-entropy: {entropy}")
    return {"modify_entropy": entropy}

# TODO Verify if we should count twice for dirs 1 deep
def code_dir_features(pr: PullRequest) -> dict:
    top_changed = []
    bottom_changed = []

    for file in pr.get_files():
        # print(f"{file.filename}")
        path = file.filename

        split_path = path.split("/")
        if len(split_path) == 1:
            continue

        top = split_path[0]
        bottom = path.rsplit('/', 1)[0]

        if top_changed.count(top) == 0:
            top_changed.append(top)

        if bottom_changed.count(bottom) == 0:
            bottom_changed.append(bottom)

    # print(f"mod_dir: {bottom_changed} | sub-sys: {top_changed}")
    # print(f"mod_dir: {len(bottom_changed)} | sub-sys: {len(top_changed)}")
    return { "modified_directories": len(bottom_changed), "subsystem_num": len(top_changed) }


def code_file_features(pr: PullRequest) -> dict:
    features = {
        "line_added": 0,
        "line_deleted": 0,
        "files_modified": 0,
        "files_added": 0,
        "files_deleted": 0,
    }

    features["line_added"] += pr.additions
    features["line_deleted"] += pr.deletions

    for file in pr.get_files():
        match file.status:
            case "added":
                features['files_added'] += 1
            case "removed":
                features['files_deleted'] += 1
            # TODO Check validity with client
            case "modified" | "renamed" | "changed":
                features["files_modified"] += 1

    return features
