import datetime
import os
from datetime import date
from github import Github, GithubException
from github.PullRequest import PullRequest

def reviewer_counts(pr: PullRequest, gapi: Github) -> dict:
    feats = {}
    repo = pr.base.repo.full_name.split('/')[1]
    bot_tags = ['do not use', 'bot', 'chatbot', 'ci', 'jenkins', repo]
    human_reviewers = 0
    bot_reviewers = 0
    for review in pr.get_reviews():
        reviewer_name = review.user.login
        if any(map(reviewer_name.lower().__contains__, bot_tags)):
            bot_reviewers += 1
        else:
            human_reviewers += 1

    feats["num_of_reviewers"] = human_reviewers
    feats["num_of_bot_reviewers"] = bot_reviewers
    return feats

def avg_reviewer_review_count(pr, review_counts: dict) -> dict:
    feats = {}
    feats["avg_reviewer_review_count"] = get_reviewer_review_count(pr.get_reviews(), review_counts)
    return feats

def avg_reviewer_exp(pr: PullRequest) -> dict:
    feats = {}
    reviewers = {}
    for review in pr.get_reviews():
        reviewer_exp = get_reviewer_last_push_in_pr(pr, review.user.login) - review.user.created_at.date()
        reviewers[review.user.login] = reviewer_exp.days
    if len(reviewers) == 0:
        feats["avg_reviewer_exp"] = 0
    else:
        # TODO: Fix time to be years instead of days
        feats["avg_reviewer_exp"] = sum(reviewers.values()) / len(reviewers)
    return feats

def get_reviewer_last_push_in_pr(pr: PullRequest, reviewer: str) -> date:
    last_change = pr.created_at.date()
    for commit in pr.get_commits():
        if commit.author.login == reviewer:
            last_change = commit.last_modified_datetime.date()
    return last_change

def get_reviewer_review_count(reviews, review_counts: dict) -> int:
    reviewers = {}
    for review in reviews:
        user = review.user.login
        reviewers[user] = reviewers.get(user, review_counts.get(user, 0))
    total_review_count = sum(reviewers.values())
    if len(reviewers) == 0:
        return 0
    return total_review_count / len(reviewers)
