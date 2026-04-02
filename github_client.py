import os

from dotenv import load_dotenv
from github import Github, Auth, GithubException

load_dotenv()


def open_pr(branch_name: str, pr_title: str, pr_description: str) -> str:
    """Open a GitHub PR for an already-pushed branch. Returns the PR URL."""
    gh = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))
    repo = gh.get_repo(os.environ["GITHUB_REPO"])
    base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main")

    try:
        pr = repo.create_pull(
            title=pr_title,
            body=pr_description,
            head=branch_name,
            base=base_branch,
        )
        print(f"  Pull request created: {pr.html_url}")
    except GithubException as e:
        if e.status == 422 and any(
            "pull request already exists" in err.get("message", "").lower()
            for err in e.data.get("errors", [])
        ):
            pulls = repo.get_pulls(
                state="open",
                head=f"{repo.owner.login}:{branch_name}",
                base=base_branch,
            )
            pr = next(iter(pulls), None)
            if pr:
                print(f"  Pull request already exists: {pr.html_url}")
            else:
                raise
        else:
            raise

    return pr.html_url
