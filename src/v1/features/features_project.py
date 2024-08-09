import datetime
from github import Github, GithubException, PaginatedList, Issue
from github.PullRequest import PullRequest

DEFAULT_MERGE_RATIO = 0.5

def project_features(pr: PullRequest, gApi: Github, cache: dict) -> dict:
    features = {}

    # Retrieve from cache if present
    project_cache = cache.get('project', {})
    changes_per_week = project_cache.get('project_changes_per_week', None)
    changes_per_author = project_cache.get('changes_per_author', None)
    merge_ratio = project_cache.get('project_merge_ratio', None)

    if None not in (changes_per_week, changes_per_author, merge_ratio):
        features = {
            'project_changes_per_week': changes_per_week,
            'changes_per_author': changes_per_author,
            'project_merge_ratio': merge_ratio
        }

        return features

    # Latest 60-day window
    now = datetime.datetime.now(datetime.timezone.utc)
    sixty_days_ago = now - datetime.timedelta(days=60)

    # PRs closed in the last 60 days
    # pulls = gApi.search_issues(f"repo:{pr.base.repo.full_name} type:pr is:closed closed:{sixty_days_ago.date()}..{now.date()}")
    pulls = gApi.get_repo(pr.base.repo.full_name).get_pulls(state='closed', direction='desc', sort='created')

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
    cache['project']['project_changes_per_week'] = changes_per_week
    cache['project']['changes_per_author'] = changes_per_author
    cache['project']['project_merge_ratio'] = merge_ratio

    features = {
        'project_changes_per_week': changes_per_week,
        'changes_per_author': changes_per_author,
        'project_merge_ratio': merge_ratio
    }

    return features
