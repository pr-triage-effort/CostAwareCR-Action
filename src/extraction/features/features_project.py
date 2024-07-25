import datetime

from github import Github
from github.PullRequest import PullRequest
from db.db import Session, Project, db_get_project


DEFAULT_MERGE_RATIO = 0.5

def project_features(pr: PullRequest, gApi: Github) -> dict:
    proj_name = pr.base.repo.full_name
    features = {}

    # Retrieve from db if present
    with Session() as session:
        project = db_get_project(proj_name, session)

    if project is not None:
        return {
            'project_changes_per_week': project.changes_per_week,
            'changes_per_author': project.changes_per_author,
            'project_merge_ratio': project.merge_ratio
        }

    # Latest 60-day window
    now = datetime.datetime.now(datetime.timezone.utc)
    sixty_days_ago = now - datetime.timedelta(days=60)

    # PRs closed in the last 60 days
    pulls = gApi.get_repo(pr.base.repo.full_name).get_pulls(state='closed')

    closed_prs = 0
    merged_prs = 0
    pr_authors = []

    for pull in pulls:
        if pull.closed_at < sixty_days_ago:
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
        changes_per_week = closed_prs * (7/60)
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

    return {
        'project_changes_per_week': changes_per_week,
        'changes_per_author': changes_per_author,
        'project_merge_ratio': merge_ratio
    }
