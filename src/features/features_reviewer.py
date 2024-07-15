from github import Github
from github.PullRequest import PullRequest

from features.features_author import author_features
from features.user_utils import is_bot_user

def reviewer_features(pr: PullRequest, api: Github, cache: dict):
    # Cached author data
    reviewer_cache = cache.get('users', {})

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
            reviewer_experience = reviewer_cache.get(reviewer_name, {}).get('author_experience', None)
            if reviewer_experience is not None:
                total_reviewer_experience += reviewer_experience
            else:
                # Compute user data
                author_features(pr, api, cache, diff_user=reviewer)
                total_reviewer_experience += reviewer_cache.get(reviewer_name, {}).get('author_experience')

            # Review count
            total_reviewer_review_num += reviewer_cache.get(reviewer_name, {}).get('author_review_number')

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
            reviewer_experience = reviewer_cache.get(reviewer_name, {}).get('author_experience', None)
            if reviewer_experience is not None:
                total_reviewer_experience += reviewer_experience
            else:
                # Compute user data
                author_features(pr, api, cache, diff_user=reviewer)
                total_reviewer_experience += reviewer_cache.get(reviewer_name, {}).get('author_experience')

            # Review count
            total_reviewer_review_num += reviewer_cache.get(reviewer_name, {}).get('author_review_number')

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
