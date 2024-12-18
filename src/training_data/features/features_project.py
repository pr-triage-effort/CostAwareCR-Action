import time
from datetime import timedelta

from github.PullRequest import PullRequest
from db.db import Session, PrProject, PullRequest as db_PR
from features.config import HISTORY_WINDOW_DAYS

HISTORY_WINDOW = timedelta(days=HISTORY_WINDOW_DAYS)
DEFAULT_MERGE_RATIO = 0.5

def project_features(prs: list[PullRequest]) -> None:
    start_time = time.time()

    for pr in prs:
        extract_project_features(pr)

    print(f"Step: \"Project Features\" executed in {time.time() - start_time}s")

def extract_project_features(pr: PullRequest) -> None:
    start_time = time.time()

    # Try retrieve from cache
    with Session() as session:
        # Previously calculated metrics
        proj_feat_pr = session.query(PrProject).where(PrProject.pr_num == pr.number).one_or_none()
        if proj_feat_pr:
            return

        # Metrics for PRs closed the same day
        sim_prs = session.query(db_PR).where(db_PR.created_at == pr.created_at.date()).all()
        sim_feats = None
        for sim_pr in sim_prs:
            if sim_pr.project_feat and sim_feats is None:
                sim_feats = sim_pr.project_feat
            elif sim_feats:
                with Session() as session:
                    feats = PrProject(
                        changes_per_week = sim_feats.changes_per_week,
                        changes_per_author = sim_feats.changes_per_author,
                        merge_ratio = sim_feats.merge_ratio
                    )
                    session.add(feats)
                    session.commit()

    # Latest N-day window
    creation_date = pr.created_at
    time_limit = creation_date - HISTORY_WINDOW

    # Merge ratio and weekly metrics
    with Session() as session:
        query = session.query(db_PR).filter(
            db_PR.state == 'closed',
            db_PR.closed_at <= creation_date,
            db_PR.closed_at >= time_limit,
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
        changes_per_week = closed_prs * (7/HISTORY_WINDOW_DAYS)
        merge_ratio = merged_prs / closed_prs

    # Cache results
    with Session() as session:
        feats = PrProject(
            changes_per_week = changes_per_week,
            changes_per_author = changes_per_author,
            merge_ratio = merge_ratio,
            pr_num = pr.number
        )

        session.add(feats)
        session.commit()
