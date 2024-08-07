import time
from datetime import datetime, timedelta, timezone
from statistics import median

from github import Github
from github.NamedUser import NamedUser
from github.PullRequest import PullRequest
from github.Repository import Repository
from sqlalchemy import func

from db.db import Session, PrAuthor, PullRequest as db_PR
from features.user_utils import is_bot_user, is_user_reviewer, try_get_total_prs, try_get_reviews_num
from features.config import HISTORY_RANGE_DAYS, DAYS_PER_YEAR, DEFAULT_MERGE_RATIO, MAX_DATA_AGE, DATETIME_NOW

HISTORY_WINDOW = timedelta(days=HISTORY_RANGE_DAYS)
EXPIRY_WINDOW = timedelta(days=MAX_DATA_AGE)

def author_features(api: Github, prs: list[PullRequest]) -> None:
    start_time = time.time()

    for pr in prs:
        step_time = time.time()
        extract_author_feature(api, pr)
        print(f"\tPR({pr.number}): {pr.title} | {time.time() - step_time}s")

    # Assign private user features based on median
    step_time = time.time()
    refresh_private_depended_stats()
    print(f"Private dependent features updated in {time.time() - step_time}s")

    print(f"Step: \"Author Features\" executed in {time.time() - start_time}s")

def extract_author_feature(api: Github, pr: PullRequest):
    author_exists = False
    author = pr.user
    repo = pr.base.repo
    pr_creation = pr.created_at

    # Try retrieve from cache
    with Session() as session:
        author_feat_pr = session.query(PrAuthor).where(PrAuthor.pr_num == pr.number).one_or_none()
        author_feat_sim = session.query(PrAuthor).where(PrAuthor.username == author.login).where(PrAuthor.pr_date == pr_creation.date()).first()

    # Return if info present
    if author_feat_pr or author_feat_sim:
        author_exists = True
        if author_feat_pr and DATETIME_NOW < author_feat_pr.last_update.replace(tzinfo=timezone.utc) + EXPIRY_WINDOW:
            return
        elif author_feat_sim and DATETIME_NOW < author_feat_sim.last_update.replace(tzinfo=timezone.utc) + EXPIRY_WINDOW:
            create_from_similar(pr, author_feat_sim)
            return

    # Experience
    registration_date = author.created_at
    experience = (pr_creation.date() - registration_date.date()).days / DAYS_PER_YEAR

    # Depending on user type, different processing
    author_feats = {}
    user_type = author_feat_pr.type if author_feat_pr else None
    match(user_type):
        case 'bot':
            author_feats = bot_author_features(repo, author, pr_creation)
        case 'private':
            author_feats = private_author_features(repo, author, pr_creation)
        case _:
            author_feats = unknown_user_features(api, repo, author, pr_creation)

    # Save/Update session
    with Session() as session:
        if author_exists:
            author_feat = session.get(PrAuthor, author_feat.id)
            author_feat.type = author_feats['type']
            author_feat.experience = experience
            author_feat.total_change_number = author_feats['total_change_number']
            author_feat.review_number = author_feats['review_number']
            author_feat.changes_per_week = author_feats['changes_per_week']
            author_feat.global_merge_ratio = author_feats['global_merge_ratio']
            author_feat.project_merge_ratio = author_feats['project_merge_ratio']
        else:
            author_feat = PrAuthor(
                username=author.login,
                type = author_feats['type'],
                experience=experience,
                review_number=author_feats['review_number'],
                total_change_number = author_feats['total_change_number'],
                changes_per_week = author_feats['changes_per_week'],
                global_merge_ratio = author_feats['global_merge_ratio'],
                project_merge_ratio = author_feats['project_merge_ratio'],
                pr_date = pr_creation.date(),
                pr_num = pr.number,
            )
            session.add(author_feat)

        session.commit()

def create_from_similar(pr: PullRequest, copy: PrAuthor):
    with Session() as session:
        author_feat = PrAuthor(
                username=copy.username,
                type = copy.type,
                experience=copy.experience,
                review_number=copy.review_number,
                total_change_number = copy.total_change_number,
                changes_per_week = copy.changes_per_week,
                global_merge_ratio = copy.global_merge_ratio,
                project_merge_ratio = copy.project_merge_ratio,
                pr_date = pr.created_at.date(),
                pr_num = pr.number,
            )
        session.add(author_feat)
        session.commit()

def bot_author_features(repo: Repository, author: NamedUser, fr_date: datetime):
    time_limit = fr_date - HISTORY_WINDOW
    author_name = author.login

    # closed/merged/total_changes
    with Session() as session:
        query = session.query(db_PR).filter(
            db_PR.author == author.login,
            db_PR.state == 'closed',
            db_PR.closed <= fr_date,
            db_PR.closed >= time_limit,
        )
        closed_prs = query.count()
        merged_prs = query.where(db_PR.merged).count()
        total_change_number = session.query(db_PR).where(db_PR.author == author_name).count()
        rev_pr_nums = session.query(db_PR.number).filter(
            db_PR.state == 'closed',
            db_PR.closed <= fr_date,
            db_PR.closed >= time_limit,
        ).all()
        rev_pr_nums = [pr.number for pr in rev_pr_nums]

    # review_num
    review_number = 0
    for pr_num in rev_pr_nums:
        pr = repo.get_pull(pr_num)
        if is_user_reviewer(pr, author):
            review_number += 1

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

def private_author_features(repo: Repository, author: NamedUser, fr_date: datetime):
    # Merge ratios
    time_limit = fr_date - HISTORY_WINDOW

    # Author project merge ratio
    with Session() as session:
        query = session.query(db_PR).filter(
            db_PR.author == author.login,
            db_PR.state == 'closed',
            db_PR.closed <= fr_date,
            db_PR.closed >= time_limit,
        )
        closed_pr_num = query.count()
        merged_pr_num = query.where(db_PR.merged).count()

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
        pub_authors = session.query(
            PrAuthor.username,
            func.avg(PrAuthor.total_change_number).label('avg_change_number'),
            func.avg(PrAuthor.review_number).label('avg_review_number'),
            func.avg(PrAuthor.changes_per_week).label('avg_changes_per_week')
        ).where(PrAuthor.type == 'public').group_by(PrAuthor.username).all()

    if len(pub_authors) > 0:
        for author in pub_authors:
            change_number.append(author.avg_change_number)
            review_number.append(author.avg_review_number)
            changes_per_week.append(author.avg_changes_per_week)

        change_number = median(change_number) if len(change_number) > 0 else 0
        review_number = median(review_number) if len(review_number) > 0 else 0
        changes_per_week = median(changes_per_week) if len(changes_per_week) > 0 else 0
    else:
        change_number = 0
        review_number = 0
        changes_per_week = 0

    with Session() as session:
        priv_authors = session.query(PrAuthor).where(PrAuthor.type == 'private').all()
        for author in priv_authors:
            author.total_change_number = change_number
            author.review_number = review_number
            author.changes_per_week = changes_per_week
        session.commit()

def unknown_user_features(api: Github, repo: Repository, author: NamedUser, fr_date: datetime):
    author_name = author.login
    time_limit = fr_date - HISTORY_WINDOW

    # Detect bot user
    if is_bot_user(author, repo):
        return bot_author_features(repo, author, fr_date)

    # Total changes created
    total_change_number = try_get_total_prs(author, api)

    # Detect private user (if private, a 422 error was thrown in try_get_total_prs)
    if total_change_number is None:
        return private_author_features(repo, author, fr_date)

    # Reviews
    review_number = try_get_reviews_num(author_name, time_limit, fr_date, api)

    # Changes per week
    global_pr_closed = api.search_issues(f"author:{author_name} type:pr is:closed closed:{time_limit.date()}..{fr_date.date()}").totalCount
    changes_per_week = global_pr_closed * (7/HISTORY_RANGE_DAYS)

    # Merge Ratios
    if global_pr_closed == 0:
        global_merge_ratio = DEFAULT_MERGE_RATIO
        project_merge_ratio = DEFAULT_MERGE_RATIO
    else:
        global_pr_merged = api.search_issues(f"author:{author_name} type:pr is:merged merged:{time_limit.date()}..{fr_date.date()}").totalCount
        global_merge_ratio = global_pr_merged /global_pr_closed

        # Author project merge ratio
        with Session() as session:
            query = session.query(db_PR).filter(
                db_PR.author == author_name,
                db_PR.state == 'closed',
                db_PR.closed <= fr_date,
                db_PR.closed >= time_limit,
            )
            proj_closed_pulls = query.count()
            proj_merged_pulls = query.where(db_PR.merged).count()

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
