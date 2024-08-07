import time
from datetime import timedelta, timezone

from github import Github
from github.PullRequest import PullRequest
from db.db import Session, Project, PullRequest as db_PR
from features.config import HISTORY_RANGE_DAYS, MAX_DATA_AGE, DATETIME_NOW

HISTORY_WINDOW = timedelta(days=HISTORY_RANGE_DAYS)
EXPIRY_WINDOW = timedelta(days=MAX_DATA_AGE)
DEFAULT_MERGE_RATIO = 0.5

def project_features(repo: str) -> None:
    start_time = time.time()

    # Retrieve from db if present
    with Session() as session:
        project = session.get(Project, repo)

    if project is not None:
        expiration = project.last_update.replace(tzinfo=timezone.utc) + EXPIRY_WINDOW
        if DATETIME_NOW < expiration:
            print(f"Project features computed in {time.time() - start_time}s")
            return
        else:
            with Session() as session:
                session.delete(project)
                session.commit()

    # Latest 60-day window
    time_limit = DATETIME_NOW - HISTORY_WINDOW

    # Merge ratio and weekly metrics
    with Session() as session:
        query = session.query(db_PR).filter(
            db_PR.state == 'closed',
            db_PR.closed <= DATETIME_NOW,
            db_PR.closed >= time_limit,
        )
        closed_prs = query.count()
        merged_prs = query.where(db_PR.merged).count()
        pr_authors = query.with_entities(db_PR.author).distinct().count()

    if closed_prs == 0:
        changes_per_author = 0
        changes_per_week = 0
        merge_ratio = DEFAULT_MERGE_RATIO
    else:
        changes_per_author = closed_prs / pr_authors
        changes_per_week = closed_prs * (7/HISTORY_RANGE_DAYS)
        merge_ratio = merged_prs / closed_prs

    # Cache results
    with Session() as session:
        project = Project(
            name = repo,
            changes_per_week = changes_per_week,
            changes_per_author = changes_per_author,
            merge_ratio = merge_ratio
        )

        session.add(project)
        session.commit()

    print(f"Project features computed in {time.time() - start_time}s")
