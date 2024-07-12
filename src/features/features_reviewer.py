import datetime
import os
from datetime import date
from github import Github, NamedUser
from github.PullRequest import PullRequest
from features.features_author import author_features

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
        if is_bot_reviewer(reviewer_name, repo_name):
            bot_reviewers += 1
        else:
            human_reviewers += 1

            # Experience
            reviewer_experience = reviewer_cache.get(reviewer_name, {}).get('author_experience', None)
            if reviewer_experience is not None:
                total_reviewer_experience += reviewer_experience
            else:
                # Compute user data
                author_features(pr, api, cache, diff_user=reviewer_name)
                total_reviewer_experience += reviewer_cache.get(reviewer_name, {}).get('author_experience')

            # Review count
            total_reviewer_review_num += reviewer_cache.get(reviewer_name, {}).get('author_review_number')  

    # Reviewer features for posted reviews
    for review in reviews:
        reviewer_name = review.user.login

        # Bot/Human reviewer
        if is_bot_reviewer(reviewer_name, repo_name):
            bot_reviewers += 1

        else:
            human_reviewers += 1

            # Experience
            reviewer_experience = reviewer_cache.get(reviewer_name, {}).get('author_experience', None)
            if reviewer_experience is not None:
                total_reviewer_experience += reviewer_experience
            else:
                # Compute user data
                author_features(pr, api, cache, diff_user=reviewer_name)
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

def is_bot_reviewer(reviewer_name: str, repo_name: str) -> bool:
    bot_tags = ['do not use', 'bot', 'chatbot', 'ci', 'jenkins', repo_name]
    if any(map(reviewer_name.lower().__contains__, bot_tags)):
        return True

    return False


# # Good to go but need to check requested reviewers
# def reviewer_counts(pr: PullRequest, gapi: Github) -> dict:
#     feats = {}
#     repo = pr.base.repo.full_name.split('/')[1]
#     bot_tags = ['do not use', 'bot', 'chatbot', 'ci', 'jenkins', repo]
#     human_reviewers = 0
#     bot_reviewers = 0
#     for review in pr.get_reviews():
#         reviewer_name = review.user.login
#         if any(map(reviewer_name.lower().__contains__, bot_tags)):
#             bot_reviewers += 1
#         else:
#             human_reviewers += 1

#     feats["num_of_reviewers"] = human_reviewers
#     feats["num_of_bot_reviewers"] = bot_reviewers
#     return feats

# def avg_reviewer_review_count(pr, review_counts: dict) -> dict:
#     feats = {}
#     feats["avg_reviewer_review_count"] = get_reviewer_review_count(pr.get_reviews(), review_counts)
#     return feats

# # Can average data from author_cache (if not in cache, call author_feature function 1 time)
# def avg_reviewer_exp(pr: PullRequest) -> dict:
#     feats = {}
#     reviewers = {}
#     for review in pr.get_reviews():
#         reviewer_exp = get_reviewer_last_push_in_pr(pr, review.user.login) - review.user.created_at.date()
#         reviewers[review.user.login] = reviewer_exp.days
#     if len(reviewers) == 0:
#         feats["avg_reviewer_exp"] = 0
#     else:
#         # TODO: Fix time to be years instead of days
#         feats["avg_reviewer_exp"] = sum(reviewers.values()) / len(reviewers)
#     return feats

# def get_reviewer_last_push_in_pr(pr: PullRequest, reviewer: str) -> date:
#     last_change = pr.created_at.date()
#     for commit in pr.get_commits():
#         if commit.author.login == reviewer:
#             last_change = commit.last_modified_datetime.date()
#     return last_change

# # Can average data from author_cache (if not in cache, call author_feature function 1 time)
# def get_reviewer_review_count(reviews, review_counts: dict) -> int:
#     reviewers = {}
#     for review in reviews:
#         user = review.user.login
#         reviewers[user] = reviewers.get(user, review_counts.get(user, 0))
#     total_review_count = sum(reviewers.values())
#     if len(reviewers) == 0:
#         return 0
#     return total_review_count / len(reviewers)
