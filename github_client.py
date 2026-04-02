import os
from github import Github, Auth, GithubException
from dotenv import load_dotenv

load_dotenv()


def create_branch_and_pr(branch_name: str, pr_title: str, pr_description: str, code_fix: str) -> str:
    """Create a GitHub branch and open a PR with the code fix. Returns the PR URL."""
    gh = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))
    repo = gh.get_repo(os.environ["GITHUB_REPO"])
    base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main")

    # Get the SHA of the base branch
    base_ref = repo.get_branch(base_branch)
    base_sha = base_ref.commit.sha

    # Create the new branch
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
        print(f"Created branch: {branch_name}")
    except GithubException as e:
        if e.status == 422:  # Branch already exists
            print(f"Branch '{branch_name}' already exists, using it.")
        else:
            raise

    # Commit the code fix as a file if there is one
    if code_fix:
        file_path = "AI_CODE_FIX.md"
        commit_message = f"chore: add AI-generated code fix\n\n{pr_title}"
        try:
            existing = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                path=file_path,
                message=commit_message,
                content=code_fix,
                sha=existing.sha,
                branch=branch_name,
            )
        except GithubException:
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=code_fix,
                branch=branch_name,
            )
        print(f"Committed code fix to {file_path} on branch {branch_name}")

    # Open the PR
    try:
        pr = repo.create_pull(
            title=pr_title,
            body=pr_description,
            head=branch_name,
            base=base_branch,
        )
        print(f"Pull request created: {pr.html_url}")
    except GithubException as e:
        if e.status == 422 and any(
            "pull request already exists" in err.get("message", "").lower()
            for err in e.data.get("errors", [])
        ):
            pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch_name}", base=base_branch)
            pr = next(iter(pulls), None)
            if pr:
                print(f"Pull request already exists: {pr.html_url}")
            else:
                raise
        else:
            raise
    return pr.html_url


if __name__ == "__main__":
    # Quick test — creates a real branch/PR in your repo
    url = create_branch_and_pr(
        branch_name="fix/test-001-sample",
        pr_title="Test: Automated PR from Jira2PR pipeline",
        pr_description="This is a test PR created by the Jira2PR automation pipeline.",
        code_fix="## Test Code Fix\n\nThis file was created automatically by the pipeline.",
    )
    print(f"PR URL: {url}")
