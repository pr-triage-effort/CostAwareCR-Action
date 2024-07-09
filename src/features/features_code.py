import math
from github.PullRequest import PullRequest

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
