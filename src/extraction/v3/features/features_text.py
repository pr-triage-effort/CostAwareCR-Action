import re
import time

from github.PullRequest import PullRequest
from db.db import Session, PrText

def text_features(prs: list[PullRequest]) -> PrText:
    start_time = time.time()

    # Reset PrText table
    with Session() as session:
        session.query(PrText).delete()
        session.commit()

    text_feats = [extract_text_feature(pr) for pr in prs]

    with Session() as session:
        session.add_all(text_feats)
        session.commit()

    print(f"Step: \"Text Features\" executed in {time.time() - start_time}s")

def extract_text_feature(pr: PullRequest) -> PrText:
    description_length = 0
    is_documentation = 0
    is_bug_fixing = 0
    is_feature = 0

    description = pr.body

    if description is not None:
        description_length = len(re.findall(r'\w+', description))

    title = pr.title
    doc_keywords = ['doc', 'docs', 'documentation', 'readme', 'license', 'copyright']
    bug_keywords = ['bug', 'fix', 'repair', 'defect']
    all_keywords = doc_keywords + bug_keywords
    for word in all_keywords:
        pattern = rf'(\b|\(|\[){re.escape(word)}(\b|\)|\]|:)'
        if re.search(pattern, title, re.IGNORECASE):
            if word in doc_keywords:
                is_documentation = 1
            elif word in bug_keywords:
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
