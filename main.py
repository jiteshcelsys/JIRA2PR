"""
Jira → Claude AI → GitHub PR pipeline.

Usage:
    python main.py                     # uses JIRA_TICKET_ID from .env
    python main.py PROJECT-456         # override ticket ID via CLI arg
"""

import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

from jira_client import get_jira_ticket
from claude_client import generate_code_fix
from github_client import open_pr

APP_DIR = "app"


def apply_changes_locally(changed_files: dict[str, str]) -> None:
    """Write Claude's changes to the local app/ directory."""
    for filename, content in changed_files.items():
        filepath = os.path.join(APP_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Written: {filepath}")


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True)


def push_branch(branch_name: str, commit_message: str) -> None:
    """Create a local branch, stage app/ changes, commit, and push."""
    base_branch = os.environ.get("GITHUB_BASE_BRANCH", "main")
    git("checkout", base_branch)
    git("pull", "origin", base_branch)
    git("checkout", "-b", branch_name)
    git("add", f"{APP_DIR}/")
    git("commit", "-m", commit_message)
    git("push", "origin", branch_name)
    print(f"  Pushed branch: {branch_name}")


def run_pipeline(ticket_id: str = None):
    print("=" * 60)
    print("Jira → Claude AI → GitHub PR Pipeline")
    print("=" * 60)

    # Step 1: Fetch Jira ticket
    print("\n[1/3] Fetching Jira ticket...")
    ticket = get_jira_ticket(ticket_id)
    print(f"  Ticket  : {ticket['id']}")
    print(f"  Summary : {ticket['summary']}")
    print(f"  Status  : {ticket['status']}")

    # Step 2: Implement changes with Claude (reads app files, uses tool use)
    print("\n[2/3] Implementing changes with Claude AI...")
    fix = generate_code_fix(ticket)
    print(f"  Branch  : {fix['branch_name']}")
    print(f"  PR Title: {fix['pr_title']}")
    print(f"  Files   : {list(fix['changed_files'].keys()) or 'none'}")

    if not fix["changed_files"]:
        print("\nClaude made no file changes — nothing to commit.")
        return None

    # Write changes locally so they show up as a diff in VS Code
    print("\n  Writing changes to app/ ...")
    apply_changes_locally(fix["changed_files"])

    print("\n" + "-" * 60)
    print("  Changes are now live in your app/ folder.")
    print("  Open the Source Control panel in VS Code (Ctrl+Shift+G)")
    print("  to review the diff before proceeding.")
    print(f"\n  PR Description that will be used:\n")
    print(fix["pr_description"])
    print("-" * 60)

    # Step 3: Developer reviews changes in VS Code, then confirms
    confirm = input("\nHappy with the changes? Create the PR? [y/N] ").strip().lower()
    if confirm != "y":
        print("\nAborted. Changes are still on disk — revert with: git checkout app/")
        return None

    # Step 4: Commit, push, open PR
    print("\n[3/3] Pushing branch and creating PR...")
    commit_message = f"{ticket['id']}: {ticket['summary']}"
    push_branch(fix["branch_name"], commit_message)

    pr_url = open_pr(
        branch_name=fix["branch_name"],
        pr_title=fix["pr_title"],
        pr_description=fix["pr_description"],
    )

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"PR URL: {pr_url}")
    print("=" * 60)
    return pr_url


if __name__ == "__main__":
    ticket_id = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(ticket_id)
