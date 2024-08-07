import re
import time

from github import Github
from github.PullRequest import PullRequest

from db.db import Session, PrText

def text_features(api: Github, repo: str, pr_status: str) -> PrText:
    start_time = time.time()

    # Reset PrText table
    with Session() as session:
        session.query(PrText).delete()
        session.commit()

    pull_requests = api.get_repo(full_name_or_id=repo).get_pulls(state=pr_status)
    text_feats = [extract_text_feature(pr) for pr in pull_requests]

    with Session() as session:
        session.add_all(text_feats)
        session.commit()

    print(f"Step: \"Text Features\" executed in {time.time() - start_time}s")


def extract_text_feature(pr: PullRequest) -> PrText:
    description_length = 0
    is_documentation = 0
    is_bug_fixing = 0
    is_feature = 0

    # TODO validate with client the change to title .vs description scanning
    description = pr.title

    if description is not None:
        description_length = len(re.findall(r'\w+', description))

        # TODO play with regex to include more keywords
        keywords = ['doc', 'docs', 'documentation', 'license', 'copyright', 'bug', 'fix', 'repair', 'defect']
        for word in keywords:
            if re.search(rf'\b{re.escape(word)}\b', description, re.IGNORECASE):
                match(word):
                    case 'doc'|'license'|'copyright':
                        is_documentation = 1
                    case 'bug'|'fix'|'defect':
                        is_bug_fixing = 1

                break

    if (is_documentation+is_bug_fixing) == 0:
        is_feature = 1

    feats = PrText(
        description_len=description_length,
        is_documentation=is_documentation,
        is_bug_fixing=is_bug_fixing,
        is_feature=is_feature,
        pr_num=pr.number
    )

    return feats
