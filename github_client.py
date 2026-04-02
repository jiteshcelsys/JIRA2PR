import os

from dotenv import load_dotenv
from github import Github, Auth, GithubException

load_dotenv()

APP_DIR = "app"


def create_branch_and_pr(
    branch_name: str,
    pr_title: str,
    pr_description: str,
    changed_files: dict[str, str],
) -> str:
    """Create a GitHub branch, commit the changed app files, and open a PR.

    Parameters
    ----------
    branch_name    : git branch to create (e.g. 'feature/scrum-2-...')
    pr_title       : PR title
    pr_description : markdown PR body
    changed_files  : {filename: new_content} relative to app/ directory

    Returns the PR URL.
    """
    gh = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))
    repo = gh.get_repo(os.environ["GITHUB_REPO"])
    base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main")

    # Get the SHA of the base branch
    base_ref = repo.get_branch(base_branch)
    base_sha = base_ref.commit.sha

    # Create the new branch
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        print(f"  Created branch: {branch_name}")
    except GithubException as e:
        if e.status == 422:  # Branch already exists
            print(f"  Branch '{branch_name}' already exists, reusing it.")
        else:
            raise

    # Commit each changed file
    for filename, content in changed_files.items():
        file_path = f"{APP_DIR}/{filename}"
        commit_message = f"{pr_title}\n\nUpdate {filename}"
        try:
            existing = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=existing.sha,
                branch=branch_name,
            )
            print(f"  Updated: {file_path}")
        except GithubException:
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch_name,
            )
            print(f"  Created: {file_path}")

    # Open the PR
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
