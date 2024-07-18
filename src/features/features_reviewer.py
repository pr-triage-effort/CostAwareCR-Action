from datetime import datetime, timedelta, timezone

from github import Github
from github.PullRequest import PullRequest
from github.NamedUser import NamedUser

from features.features_author import author_features
from features.user_utils import is_bot_user, try_get_reviews_num

DAYS_PER_YEAR = 365.25
TIME_WINDOW_DAYS = 60

def reviewer_features(pr: PullRequest, api: Github, cache: dict):
    # Cached author data
    user_cache = cache.get('users', {})

    # Temp data
    requested_reviewers = pr.requested_reviewers
    reviews = pr.get_reviews()
    repo_name = pr.base.repo.full_name.split('/')[1]
    bot_reviewers = 0
    human_reviewers = 0
    total_reviewer_experience = 0
    total_reviewer_review_num = 0

    # Reviewer feats for requested reviewers
    for reviewer in requested_reviewers:
        reviewer_name = reviewer.login

        # Bot/Human reviewer
        if is_bot_user(reviewer_name, repo_name):
            bot_reviewers += 1
        else:
            human_reviewers += 1

            # Experience
            total_reviewer_experience += get_reviewer_experience(pr, reviewer, user_cache)
            # Review count
            total_reviewer_review_num += user_cache.get(reviewer_name, {}).get('author_review_number')

    # Reviewer features for posted reviews
    for review in reviews:
        reviewer = review.user
        reviewer_name = reviewer.login

        # Bot/Human reviewer
        if is_bot_user(reviewer_name, repo_name):
            bot_reviewers += 1

        else:
            human_reviewers += 1

            # Experience
            total_reviewer_experience += get_reviewer_experience(pr, reviewer, user_cache)
            # Review count
            total_reviewer_review_num += user_cache.get(reviewer_name, {}).get('author_review_number')

    # Compute reviewer features
    avg_reviewer_experience = 0
    avg_reviewer_review_count = 0

    if human_reviewers > 0:
        avg_reviewer_experience = total_reviewer_experience / human_reviewers
        avg_reviewer_review_count = total_reviewer_review_num / human_reviewers

    return {
        'num_of_reviewers': human_reviewers,
        'num_of_bot_reviewers': bot_reviewers,
        'avg_reviewer_experience': avg_reviewer_experience,
        'avg_reviewer_review_count': avg_reviewer_review_count
    }

def get_reviewer_experience(pr: PullRequest, user: NamedUser, user_cache: dict) -> float:
    username = user.login

    # Try retrieve from cache
    experience = user_cache.get(username, {}).get('author_experience', None)

    if experience is not None:
        return experience

    # Else calculate
    registration_date = user.created_at
    latest_revision = pr.created_at
    experience = (latest_revision.date() - registration_date.date()).days / DAYS_PER_YEAR

    # Cache result
    if user not in user_cache:
        user_cache[username] = {
            'author_experience': experience
        }
    else:
        user_cache[username]['author_experience'] = experience

    return experience

def get_reviewer_review_cnt(user: NamedUser, user_cache: dict, api: Github) -> int:
    username = user.login

    # Try retrieve from cache
    reviews = user_cache.get(username, {}).get('author_review_number', None)

    if reviews is not None:
        return reviews

    # Else calculate
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=TIME_WINDOW_DAYS)
    reviews = try_get_reviews_num(username, start_date, now, api)

    # Cache result
    if reviews is not None:
        if user not in user_cache:
            user_cache[username] = {
                'author_review_number': reviews
            }
    else:
        user_cache[username]['author_review_number'] = reviews

    return reviews
