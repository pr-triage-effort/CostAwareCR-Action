import time
from datetime import timedelta

from github import Github
from github.Repository import Repository
from github.PullRequest import PullRequest
from github.NamedUser import NamedUser
from db.db import Session, User, PrReviewers

from features.user_utils import is_bot_user, is_user_reviewer, try_get_reviews_num
from features.config import HISTORY_WINDOW_DAYS, DAYS_PER_YEAR

HISTORY_WINDOW = timedelta(days=HISTORY_WINDOW_DAYS)

def reviewer_features(api: Github, prs: list[PullRequest]):
    start_time = time.time()

    reviewer_feats = [extract_reviewer_features(api, pr) for pr in prs]

    with Session() as session:
        session.add_all(reviewer_feats)
        session.commit()

    print(f"Step: \"Reviewer Features\" executed in {time.time() - start_time}s")

def extract_reviewer_features(api: Github, pr: PullRequest):
    # Temp data
    repo = pr.base.repo
    requested_reviewers = pr.requested_reviewers
    reviews = [review for review in pr.get_reviews() if review.user is not None]
    bot_reviewers = 0
    human_reviewers = 0
    total_reviewer_experience = 0
    total_reviewer_review_num = 0

    # Reviewer feats for requested reviewers
    for reviewer in requested_reviewers:
        # Bot/Human reviewer
        if is_bot_user(reviewer, repo):
            bot_reviewers += 1
        else:
            human_reviewers += 1
            exp, revs = get_reviewer_feats(pr, repo, reviewer, api)
            total_reviewer_experience += exp
            total_reviewer_review_num += revs

    # Reviewer features for posted reviews
    for review in reviews:
        reviewer = review.user

        # Bot/Human reviewer
        if is_bot_user(reviewer, repo):
            bot_reviewers += 1
        else:
            human_reviewers += 1
            exp, revs = get_reviewer_feats(pr, repo, reviewer, api)
            total_reviewer_experience += exp
            total_reviewer_review_num += revs

    # Compute reviewer features
    avg_reviewer_experience = 0
    avg_reviewer_review_count = 0

    if human_reviewers > 0:
        avg_reviewer_experience = total_reviewer_experience / human_reviewers
        avg_reviewer_review_count = total_reviewer_review_num / human_reviewers

    return PrReviewers(
        humans = human_reviewers,
        bots = bot_reviewers,
        avg_experience = avg_reviewer_experience,
        avg_reviews = avg_reviewer_review_count,
        pr_num = pr.number
    )

def get_reviewer_feats(pull: PullRequest, repo: Repository, user: NamedUser, api: Github):
    username = user.login
    user_type = 'public'
    open_date = pull.created_at

    # Try retrieve from cache
    with Session() as session:
        db_user = session.query(User).where(User.username == username).where(User.pr_date == open_date.date()).first()

    if db_user is not None:
        return db_user.experience, db_user.review_number

    # Calc experience
    registration_date = user.created_at
    experience = (open_date.date() - registration_date.date()).days / DAYS_PER_YEAR

    # Calc review_num
    limit_date = open_date - HISTORY_WINDOW
    reviews = try_get_reviews_num(username, limit_date, open_date, api)

    if reviews is None:
        reviews = 0
        user_type = 'private'
        prs = repo.get_pulls(state='closed')
        for pr in prs:
            if pr.closed_at > open_date:
                continue
            if pr.closed_at < limit_date:
                break
            if is_user_reviewer(pr, user):
                reviews += 1

    with Session() as session:
        db_user = User(
            username=username,
            type=user_type,
            experience=experience,
            review_number=reviews,
            pr_date=open_date.date(),
            pr_num=pull.number
        )
        session.add(db_user)
        session.commit()

    return experience, reviews
