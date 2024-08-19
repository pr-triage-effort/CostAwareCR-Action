import time
from datetime import timedelta, timezone

from github import Github
from github.PullRequest import PullRequest
from db.db import Session, PrProject, PullRequest as db_PR
from features.config import HISTORY_RANGE_DAYS, MAX_DATA_AGE, DATETIME_NOW

HISTORY_WINDOW = timedelta(days=HISTORY_RANGE_DAYS)
DEFAULT_MERGE_RATIO = 0.5

def project_features(api: Github, prs: list[PullRequest]) -> None:
    start_time = time.time()

    for pr in prs:
        extract_project_feature(pr)

    print(f"Step: \"Author Features\" executed in {time.time() - start_time}s")

def extract_project_feature(pr: PullRequest) -> None:
    start_time = time.time()

    # Try retrieve from cache
    with Session() as session:
        # Previously calculated metrics
        proj_feat_pr = session.query(PrProject).where(PrProject.pr_num == pr.number).one_or_none()
        if proj_feat_pr:
            return

        # Metrics for PRs closed the same day
        sim_prs = session.query(db_PR).where(db_PR.closed == pr.closed_at.date()).all()
        for sim_pr in sim_prs:
            if sim_pr.project_feat:
                sim_feat = sim_pr.project_feat
                with Session() as session:
                    feats = PrProject(
                        changes_per_week = sim_feat.changes_per_week,
                        changes_per_author = sim_feat.changes_per_author,
                        merge_ratio = sim_feat.merge_ratio
                    )
                    session.add(feats)
                    session.commit()
                return

    # Latest N-day window
    closure_date = pr.closed_at
    time_limit = closure_date - HISTORY_WINDOW

    # Merge ratio and weekly metrics
    with Session() as session:
        query = session.query(db_PR).filter(
            db_PR.state == 'closed',
            db_PR.closed <= closure_date,
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
        feats = PrProject(
            changes_per_week = changes_per_week,
            changes_per_author = changes_per_author,
            merge_ratio = merge_ratio
        )

        session.add(feats)
        session.commit()
        
    print(f"Step: \"Project Features\" executed in {time.time() - start_time}s")
