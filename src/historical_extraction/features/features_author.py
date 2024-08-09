import time
from datetime import datetime, timedelta, timezone
from statistics import median

from github import Github
from github.NamedUser import NamedUser
from github.PullRequest import PullRequest
from github.Repository import Repository
from db.db import Session, User, db_get_user

from features.user_utils import is_bot_user, is_user_reviewer, try_get_total_prs, try_get_reviews_num
from features.config import HISTORY_RANGE_DAYS, DAYS_PER_YEAR, DEFAULT_MERGE_RATIO


NOW = datetime.now(timezone.utc)
TIME_LIMIT = NOW - timedelta(days=HISTORY_RANGE_DAYS)

def author_features(api: Github, repo: str, pr_status: str) -> None:
    start_time = time.time()

    pull_requests = api.get_repo(full_name_or_id=repo).get_pulls(state=pr_status)
    for pr in pull_requests:
        step_time = time.time()
        extract_author_feature(api, pr)
        print(f"\tPR({pr.number}): {pr.title} | {time.time() - step_time}s")

    # Assign private user features based on median
    step_time = time.time()
    refresh_private_depended_stats()
    print(f"Private dependent features updated in {time.time() - step_time}s")

    print(f"Step: \"Author Features\" executed in {time.time() - start_time}s")

def extract_author_feature(api: Github, pr: PullRequest):
    author = pr.user
    repo = pr.base.repo

    # Try retrieve from cache
    with Session() as session:
        db_user = session.query(User).where(User.username == author.login).one_or_none()

    reuse_data = True  # TODO Change dynamicaly to refresh aging data
    # Return if info present
    if db_user is not None and db_user.tag == 'F':
        return

    # Experience
    experience = db_user.experience
    if experience is None:
        registration_date = author.created_at
        latest_revision = pr.created_at
        experience = (latest_revision.date() - registration_date.date()).days / DAYS_PER_YEAR

    # Depending on user type, different processing
    author_feats = {}
    match(db_user.type):
        case 'bot':
            author_feats = bot_author_features(repo, author)
        case 'private':
            author_feats = private_author_features(repo, author)
        case _:
            author_feats = unknown_user_features(api, repo, author, db_user, reuse_data)

    # Save/Update session
    with Session() as session:
        db_user = session.get(User, db_user.id)
        db_user.tag = 'F'
        db_user.type = author_feats['type']
        db_user.experience = experience
        db_user.total_change_number = author_feats['total_change_number']
        db_user.review_number = author_feats['review_number']
        db_user.changes_per_week = author_feats['changes_per_week']
        db_user.global_merge_ratio = author_feats['global_merge_ratio']
        db_user.project_merge_ratio = author_feats['project_merge_ratio']
        session.commit()

def bot_author_features(repo: Repository, author: NamedUser):
    author_name = author.login
    total_change_number = 0
    review_number = 0
    closed_prs = 0
    merged_prs = 0

    pull_requests = repo.get_pulls()
    for pr in pull_requests:
        # Change number
        if pr.user.login == author_name:
            total_change_number += 1

        if pr.state == 'closed' and pr.closed_at >= TIME_LIMIT:
            if is_user_reviewer(pr, author):
                review_number += 1
            elif pr.user.login == author_name:
                closed_prs += 1
                if pr.merged:
                    merged_prs += 1

    if closed_prs > 0:
        changes_per_week = closed_prs * (7/HISTORY_RANGE_DAYS)
        project_merge_ratio = merged_prs / closed_prs
    else:
        changes_per_week = 0
        project_merge_ratio = DEFAULT_MERGE_RATIO

    global_merge_ratio = project_merge_ratio

    return {
        'type': 'bot',
        'total_change_number': total_change_number,
        'review_number': review_number,
        'changes_per_week': changes_per_week,
        'global_merge_ratio': global_merge_ratio,
        'project_merge_ratio': project_merge_ratio,
    }

def private_author_features(repo: Repository, author: NamedUser):
    # Merge ratios
    closed_pr_num = 0
    merged_pr_num = 0

    prs = repo.get_pulls(state='closed')
    for pr in prs:
        if pr.closed_at < TIME_LIMIT:
            break

        if pr.user.login == author.login:
            closed_pr_num += 1
            if pr.merged:
                merged_pr_num += 1

    global_merge_ratio = DEFAULT_MERGE_RATIO
    if closed_pr_num > 0:
        project_merge_ratio = merged_pr_num / closed_pr_num
    else:
        project_merge_ratio = DEFAULT_MERGE_RATIO

    return {
        'type': 'private',
        'total_change_number': None,
        'review_number': None,
        'changes_per_week': None,
        'global_merge_ratio': global_merge_ratio,
        'project_merge_ratio': project_merge_ratio,
    }

def refresh_private_depended_stats():
    change_number = []
    review_number = []
    changes_per_week = []

    with Session() as session:
        pub_authors = session.query(User).where(User.type == 'public').all()

    if len(pub_authors) > 0:
        for author in pub_authors:
            if author.tag == 'F':
                change_number.append(author.total_change_number)
                review_number.append(author.review_number)
                changes_per_week.append(author.changes_per_week)

        change_number = median(change_number) if len(change_number) > 0 else 0
        review_number = median(review_number) if len(review_number) > 0 else 0
        changes_per_week = median(changes_per_week) if len(changes_per_week) > 0 else 0
    else:
        change_number = 0
        review_number = 0
        changes_per_week = 0

    with Session() as session:
        priv_authors = session.query(User).where(User.type == 'private').where(User.tag == 'F')
        for author in priv_authors:
            author.total_change_number = change_number
            author.review_number = review_number
            author.changes_per_week = changes_per_week
        session.commit()

def unknown_user_features(api: Github, repo: Repository, author: NamedUser, db_user: User, reuse_data: bool):
    author_name = author.login

    # Detect bot user
    if is_bot_user(author, repo):
        return bot_author_features(repo, author)
    
    # Total changes created
    total_change_number = try_get_total_prs(author, api)

    # Detect private user (if private, a 422 error was thrown in try_get_total_prs)
    if total_change_number is None:
        return private_author_features(repo, author)

    # Reviews
    if reuse_data and db_user.review_number is not None:
        review_number = db_user.review_number
    else:
        review_number = try_get_reviews_num(author_name, TIME_LIMIT, NOW, api)

    # Changes per week
    global_pr_closed = api.search_issues(f"author:{author_name} type:pr is:closed closed:{TIME_LIMIT.date()}..{NOW.date()}").totalCount
    changes_per_week = global_pr_closed * (7/HISTORY_RANGE_DAYS)

    # Merge Ratios
    if global_pr_closed == 0:
        global_merge_ratio = DEFAULT_MERGE_RATIO
        project_merge_ratio = DEFAULT_MERGE_RATIO
    else:
        global_pr_merged = api.search_issues(f"author:{author_name} type:pr is:merged merged:{TIME_LIMIT.date()}..{NOW.date()}").totalCount
        global_merge_ratio = global_pr_merged /global_pr_closed

        # Author project merge ratio
        repo_pulls = repo.get_pulls(state='closed')
        proj_closed_pulls = 0
        proj_merged_pulls = 0

        for pull in repo_pulls:
            if pull.closed_at < TIME_LIMIT:
                break
            if pull.user.login == author_name:
                proj_closed_pulls += 1
                if pull.merged:
                    proj_merged_pulls += 1

        if proj_closed_pulls == 0:
            project_merge_ratio = DEFAULT_MERGE_RATIO
        else:
            project_merge_ratio = proj_merged_pulls / proj_closed_pulls

    return {
        'type': 'public',
        'total_change_number': total_change_number,
        'review_number': review_number,
        'changes_per_week': changes_per_week,
        'global_merge_ratio': global_merge_ratio,
        'project_merge_ratio': project_merge_ratio,
    }
