import datetime
from github import Github, GithubException, PaginatedList, Issue, NamedUser
from github.PullRequest import PullRequest

DEFAULT_MERGE_RATIO = 0.5

def author_features(pr: PullRequest, api: Github, cache: dict, diff_user: str = None):
    
    # Author username
    author = pr.user.login
    if diff_user is not None:
        author = diff_user

    # Try retrieve from cache
    author_cache = cache.get('users', {}).get(author, {})
    experience = author_cache.get('total_change_number', None)
    change_number = author_cache.get('total_change_number', None)
    review_number = author_cache.get('author_review_number', None)
    changes_per_week = author_cache.get('author_changes_per_week', None)
    global_merge_ratio = author_cache.get('author_merge_ratio', None)
    project_merge_ratio = author_cache.get('author_merge_ratio_in_project', None)
    
    # If present, return results
    if None not in (experience, change_number, review_number, changes_per_week, global_merge_ratio, project_merge_ratio):
        return {
            'author_experience': experience,
            'total_change_number': change_number,
            'author_review_number': review_number,
            'author_changes_per_week': changes_per_week,
            'author_merge_ratio': global_merge_ratio,
            'author_merge_ratio_in_project': project_merge_ratio
        }
    
    # Author experience
    registration_date = pr.user.created_at
    latest_revision = pr.created_at
    experience = (latest_revision.date() - registration_date.date()).days / 365.25
    
    # Author total change number
    change_number = api.search_issues(f"is:pr author:{author}").totalCount
    
    # 60-day window
    now = datetime.datetime.now(datetime.timezone.utc)
    sixty_days_ago = now - datetime.timedelta(days=60)
    
    # Author review number
    review_number = api.search_issues(f"type:pr reviewed-by:{author} closed:{sixty_days_ago.date()}..{now.date()}").totalCount
    review_number += api.search_issues(f"type:pr review-requested:{author} closed:{sixty_days_ago.date()}..{now.date()}").totalCount
    
    # Author changes per week
    global_pr_closed = api.search_issues(f"author:{author} type:pr is:closed closed:{sixty_days_ago.date()}..{now.date()}").totalCount
    changes_per_week = global_pr_closed * (7/60)
    
    # Author global merge ratio
    if global_pr_closed == 0:
        global_merge_ratio = DEFAULT_MERGE_RATIO
        project_merge_ratio = DEFAULT_MERGE_RATIO
    else:
        global_pr_merged = api.search_issues(f"author:{author} type:pr is:merged merged:{sixty_days_ago.date()}..{now.date()}").totalCount
        global_merge_ratio = global_pr_merged /global_pr_closed
        
        # Author project merge ratio
        project_pr_closed = api.search_issues(f"author:{author} repo:{pr.base.repo.full_name} type:pr is:closed closed:{sixty_days_ago.date()}..{now.date()}").totalCount
        if project_pr_closed == 0:
            project_merge_ratio = DEFAULT_MERGE_RATIO
        else:
            project_pr_merged = api.search_issues(f"author:{author} repo:{pr.base.repo.full_name} type:pr is:merged merged:{sixty_days_ago.date()}..{now.date()}").totalCount
            project_merge_ratio = project_pr_merged / project_pr_closed
            
    # Cache results
    if author not in cache['users']:
        cache['users'][author] = {}

    cache['users'][author]['author_experience'] = experience
    cache['users'][author]['total_change_number'] = change_number
    cache['users'][author]['author_review_number'] = review_number
    cache['users'][author]['author_changes_per_week'] = changes_per_week
    cache['users'][author]['author_merge_ratio'] = global_merge_ratio
    cache['users'][author]['author_merge_ratio_in_project'] = project_merge_ratio
    
    return {
            'author_experience': experience,
            'total_change_number': change_number,
            'author_review_number': review_number,
            'author_changes_per_week': changes_per_week,
            'author_merge_ratio': global_merge_ratio,
            'author_merge_ratio_in_project': project_merge_ratio
        }


# Not used, will be removed when edge case functions are created
def is_private_profile(user: NamedUser) -> bool:
    try:
        public_events = user.get_public_events()
        if public_events.totalCount == 0:
            return True
    except GithubException as e:
        if e.status == 403:  # Forbidden error may indicate a private profile
            return True
        else:
            raise e
    return False

def author_review_number(pr: PullRequest, gApi: Github, cache: dict):
    # Author username
    author = pr.user.login

    # Try retrieve from cache
    author_cache = cache.get('users', {}).get(author, {})
    result = author_cache.get('author_review_number', None)

    if result is not None:
        return result

    # Latest 60-day window
    now = datetime.datetime.now(datetime.timezone.utc)
    sixty_days_ago = now - datetime.timedelta(days=60)

    # PRs where the author was requested/reviewed
    review_count = 0
    if not is_private_profile(pr.user):
        review_count += gApi.search_issues(f"type:pr reviewed-by:{author} closed:{sixty_days_ago.date()}..{now.date()}").totalCount
        review_count += gApi.search_issues(f"type:pr review-requested:{author} closed:{sixty_days_ago.date()}..{now.date()}").totalCount

        

    # Handle authors with private profiles
    else :
        # Get all closed PRs
        pulls_involving_author = gApi.get_repo(full_name_or_id=pr.base.repo.full_name).get_pulls(state='closed')

        for pull in pulls_involving_author:
            if pull.closed_at >= sixty_days_ago and author_is_reviewer(pull, author):
                review_count += 1

    # Cache result
    if author not in cache['users']:
        cache['users'][author] = {}

    cache['users'][author]['author_review_number'] = review_count
    
    return review_count

def author_is_reviewer(pull: PullRequest, author: str) -> int:
    if author != pull.user.login:

        # Check through reviews
        reviews = pull.get_reviews()
        for review in reviews:
            if review.user.login == author:
                return True

    return False

def total_change_number(pr: PullRequest, gApi: Github, cache: dict):
    # Author username
    author = pr.user.login

    # Try retrieve from cache
    author_cache = cache.get('users', {}).get(author, {})
    pr_count = author_cache.get('total_change_number', None)

    if pr_count is not None:
        return pr_count

    try:
        pr_count = gApi.search_issues(f"is:pr author:{author}").totalCount

    # Handle possibly private author activity
    except GithubException as e:
        if e.status == 422:
            # Get all closed PRs
            pr_count = 0
            repo_prs = gApi.get_repo(full_name_or_id=pr.base.repo.full_name).get_pulls()
            for pull in repo_prs:
                if pull.user.location == author:
                    pr_count += 1

        else:
            raise e  

    # Cache result
    if author not in cache['users']:
        cache['users'][author] = {}

    cache['users'][author]['total_change_number'] = pr_count

    return pr_count

# TODO what value to assign if private profile
def author_changes_per_week(pr: PullRequest, gApi: Github, cache: dict):
    # Author username
    author = pr.user.login

    # Try retrieve from cache
    author_cache = cache.get('users', {}).get(author, {})
    changes_per_week = author_cache.get('author_changes_per_week', None)

    if changes_per_week is not None:
        return changes_per_week
    
    # Changes per week
    num_weeks = 60 / 7
    now = datetime.datetime.now(datetime.timezone.utc)
    sixty_days_ago = now - datetime.timedelta(days=60)

    try:
        num_closed_pulls = gApi.search_issues(f"author:{author} type:pr is:closed closed:{sixty_days_ago.date()}..{now.date()}").totalCount
        changes_per_week = num_closed_pulls / num_weeks

    # Handle possibly private author activity
    except GithubException as e:
        if e.status == 422:
            # Manually check all prs and compare author
            closed_in_project = gApi.get_repo(full_name_or_id=pr.base.repo.full_name).get_pulls(state='closed')
            num_pulls = 0
            for pull in closed_in_project:
                if pull.user.login == author and pr.closed_at >= sixty_days_ago:
                    num_pulls += 1
            
            changes_per_week = num_pulls / num_weeks
        else:
            raise e  

    # Cache result
    if author not in cache['users']:
        cache['users'][author] = {}

    cache['users'][author]['author_changes_per_week'] = changes_per_week
    
    return changes_per_week