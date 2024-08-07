import time
from datetime import datetime, timedelta, timezone

from github import Github
from db.db import Session, Project, db_get_project
from features.config import HISTORY_LIMIT, HISTORY_RANGE_DAYS, MAX_DATA_AGE


DEFAULT_MERGE_RATIO = 0.5

def project_features(api: Github, proj_name: str) -> None:
    start_time = time.time()

    # Retrieve from db if present
    with Session() as session:
        project = db_get_project(proj_name, session)

    if project is not None:
        expiration = project.last_update.replace(tzinfo=timezone.utc) + timedelta(days=MAX_DATA_AGE)
        if datetime.now(timezone.utc) < expiration:
            print(f"Project features computed in {time.time() - start_time}s")
            return
        else:
            with Session() as session:
                session.delete(project)
                session.commit()

    # Latest 60-day window
    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(days=HISTORY_RANGE_DAYS) if HISTORY_LIMIT else None

    # PRs closed in the last 60 days
    repo = api.get_repo(proj_name)
    pulls = repo.get_pulls(state='closed')

    closed_prs = 0
    merged_prs = 0
    pr_authors = []

    for pull in pulls:
        if time_limit and pull.closed_at < time_limit:
            break

        closed_prs += 1

        # Check for merge
        if pull.merged:
            merged_prs += 1

        # Check for unique author
        if pr_authors.count(pull.user.login) == 0:
            pr_authors.append(pull.user.login)

    if closed_prs == 0:
        changes_per_author = 0
        changes_per_week = 0
        merge_ratio = DEFAULT_MERGE_RATIO
    else:
        changes_per_author = closed_prs / len(pr_authors)
        if HISTORY_LIMIT:
            changes_per_week = closed_prs * (7/HISTORY_RANGE_DAYS)
        else:
            changes_per_week = closed_prs * (7/ (now - repo.created_at).days)
        merge_ratio = merged_prs / closed_prs

    # Cache results
    with Session() as session:
        project = Project(
            name = proj_name,
            changes_per_week = changes_per_week,
            changes_per_author = changes_per_author,
            merge_ratio = merge_ratio
        )

        session.add(project)
        session.commit()

    print(f"Project features computed in {time.time() - start_time}s")
