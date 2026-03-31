"""
Jira → Claude AI → GitHub PR pipeline.

Usage:
    python main.py                     # uses JIRA_TICKET_ID from .env
    python main.py PROJECT-456         # override ticket ID via CLI arg
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from jira_client import get_jira_ticket
from claude_client import generate_code_fix
from github_client import create_branch_and_pr


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

    # Step 2: Generate code fix with Claude
    print("\n[2/3] Generating code fix with Claude AI...")
    fix = generate_code_fix(ticket)
    print(f"  Branch  : {fix['branch_name']}")
    print(f"  PR Title: {fix['pr_title']}")

    # Step 3: Create GitHub branch and PR
    print("\n[3/3] Creating GitHub branch and PR...")
    pr_url = create_branch_and_pr(
        branch_name=fix["branch_name"],
        pr_title=fix["pr_title"],
        pr_description=fix["pr_description"],
        code_fix=fix["code_fix"],
    )

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"PR URL: {pr_url}")
    print("=" * 60)
    return pr_url


if __name__ == "__main__":
    ticket_id = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(ticket_id)
