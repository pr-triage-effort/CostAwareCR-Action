import datetime
from github import Github, GithubException, PaginatedList, Issue, NamedUser
from github.PullRequest import PullRequest

DEFAULT_MERGE_RATIO = 0.5

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

def author_features(pr: PullRequest, api: Github, cache: dict):
    
    # Author username
    author = pr.user.login

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
    experience = (latest_revision.date() - registration_date.date())
    
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
            'author experience': experience,
            'total_change_number': change_number,
            'author_review_number': review_number,
            'author_changes_per_week': changes_per_week,
            'author_merge_ratio': global_merge_ratio,
            'author_merge_ratio_in_project': project_merge_ratio
        }

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

# TODO The experience is in days or years
def author_experience(pr: PullRequest, gApi: Github, cache: dict):
    # Author username
    author = pr.user.login

    # Try retrieve from cache
    author_cache = cache.get('users', {}).get(author, {})
    experience = author_cache.get('total_change_number', None)

    if experience is not None:
        return experience
    
    # TODO verify that we use Github as reference and not first commit ro project
    # Get authors registration date
    registration_date = pr.user.created_at

    # Get latest pr revision date by the author
    latest_revision = pr.created_at
    
    # TODO do we use latest author commit in PR/ latest PR mod/ PR created_at
    commits = pr.get_commits()
    for commit in commits:
        if commit.author == author and commit.last_modified_datetime > latest_revision:
            latest_revision = commit.last_modified_datetime

    experience = latest_revision.date() - registration_date.date()

    # Cache result
    if author not in cache['users']:
        cache['users'][author] = {}

    cache['users'][author]['author_experience'] = experience.days
    
    return experience.days

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

def author_merge_ratios(pr: PullRequest, gApi: Github, cache: dict):
    features = {}

    # Author username
    author = pr.user.login
    default_merge_ratio = 0.5

    # Latest 60-day window
    now = datetime.datetime.now(datetime.timezone.utc)
    sixty_days_ago = now - datetime.timedelta(days=60)

    # Retrieve from cache if present
    author_cache = cache.get('users', {}).get(author, {})
    ratio1 = author_cache.get('author_merge_ratio', None)
    ratio2 = author_cache.get('author_merge_ratio_in_project', None)

    if None not in (ratio1, ratio2):
        features["author_merge_ratio"] = ratio1
        features["author_merge_ratio_in_project"] = ratio2

        return features

    try:
        # Authors PRs in the last 60 days
        author_pr_closed = gApi.search_issues(f"author:{author} type:pr is:closed closed:{sixty_days_ago.date()}..{now.date()}").totalCount
        author_pr_merged = gApi.search_issues(f"author:{author} type:pr is:merged merged:{sixty_days_ago.date()}..{now.date()}").totalCount

        # Authors in project PRs in the last 60 days
        author_pr_closed_in_project = gApi.search_issues(f"author:{author} repo:{pr.base.repo.full_name} type:pr is:closed closed:{sixty_days_ago.date()}..{now.date()}").totalCount
        author_pr_merged_in_project = gApi.search_issues(f"author:{author} repo:{pr.base.repo.full_name} type:pr is:merged merged:{sixty_days_ago.date()}..{now.date()}").totalCount

        # Determine global merge ratio
        if author_pr_closed == 0:
            features["author_merge_ratio"] = default_merge_ratio
        else:
            features["author_merge_ratio"] = author_pr_merged / author_pr_closed

        # Determine project merge ratio
        if author_pr_closed_in_project == 0:
            features["author_merge_ratio_in_project"] = default_merge_ratio
        else:
            features["author_merge_ratio_in_project"] = author_pr_merged_in_project / author_pr_closed_in_project

    # Handle possibly private author activity
    except GithubException as e:
        if e.status == 422:
            # Assign default merge ratio if user's activity is private
            features["author_merge_ratio"] = default_merge_ratio
            features["author_merge_ratio_in_project"] = default_merge_ratio
        else:
            raise e    

    # Cache results
    if author not in cache['users']:
        cache['users'][author] = {}

    cache['users'][author]['author_merge_ratio'] = features.get('author_merge_ratio')
    cache['users'][author]['author_merge_ratio_in_project'] = features.get('author_merge_ratio_in_project')

    return features

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