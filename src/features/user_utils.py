from github import Github ,GithubException
from github.NamedUser import NamedUser
from github.PullRequest import PullRequest

def is_bot_user(username: str, repo_name: str) -> bool:
    bot_tags = ['do not use', 'bot', 'chatbot', 'ci', 'jenkins', repo_name]
    if any(map(username.lower().__contains__, bot_tags)):
        return True

    return False

# When trying to fetch private user data through issue search and exploring props
# A code 422 exception is raised
def try_get_total_prs(user: NamedUser, api: Github) -> bool:
    try:
        change_num = api.search_issues(f"is:pr author:{user.login}").totalCount

    except GithubException as e:
        if e.status == 422:
            return None
        raise e
        
    return change_num

def is_user_reviewer(pr: PullRequest, user: NamedUser):
    if user != pr.user.login:
        # Check in requested list
        if user.login in pr.requested_reviewers:
            return True

        # Check through reviews
        reviews = pr.get_reviews()
        for review in reviews:
            if review.user.login == user:
                return True

    return False