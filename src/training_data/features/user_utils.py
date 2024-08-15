import re
from datetime import datetime

from github import Github ,GithubException
from github.NamedUser import NamedUser
from github.PullRequest import PullRequest
from github.Repository import Repository

# TODO time execution
def is_bot_user(user: NamedUser, repo: Repository) -> bool:
    if user.type == 'Bot':
        return True

    username = user.login
    repo_name = repo.full_name.split('/')[1]
    bot_tags = ['do not use', 'bot', 'chatbot', 'ci', 'jenkins', repo_name]
    bot_pattern = r'(-|^|\b)({})(-|$|\b)'.format('|'.join(bot_tags))
    bot_regex = re.compile(bot_pattern)

    if bot_regex.search(username):
        return True

    return False

def is_user_reviewer(pr: PullRequest, user: NamedUser):
    if user.login != pr.user.login:
        # Check in requested list
        for reviewer in pr.requested_reviewers:
            if user.login == reviewer.login:
                return True

        # Check through reviews
        reviews = pr.get_reviews()
        for review in reviews:
            if review.user.login == user.login:
                return True

    return False

# When trying to fetch private user data through issue search and exploring props
# A code 422 exception is raised
def try_get_total_prs(user: NamedUser, api: Github) -> int:
    try:
        change_num = api.search_issues(f"is:pr author:{user.login}").totalCount
    except GithubException as e:
        if e.status == 422:
            return None

    return change_num

def try_get_reviews_num(username: str, start_date: datetime, end_date: datetime, api: Github) -> int:
    try:
        review_number = api.search_issues(f"type:pr reviewed-by:{username} closed:{start_date.date()}..{end_date.date()}").totalCount
        review_number += api.search_issues(f"type:pr review-requested:{username} closed:{start_date.date()}..{end_date.date()}").totalCount
    except GithubException as e:
        if e.status == 422:
            return None

    return review_number
