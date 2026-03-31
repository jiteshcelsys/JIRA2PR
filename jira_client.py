import os
from jira import JIRA
from dotenv import load_dotenv

load_dotenv()


def get_jira_ticket(ticket_id: str = None) -> dict:
    """Fetch a Jira ticket and return its key details."""
    client = JIRA(
        server=os.environ["JIRA_URL"],
        basic_auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"]),
    )

    ticket_id = ticket_id or os.environ["JIRA_TICKET_ID"]
    issue = client.issue(ticket_id)

    return {
        "id": issue.key,
        "summary": issue.fields.summary,
        "description": issue.fields.description or "",
        "status": issue.fields.status.name,
        "issue_type": issue.fields.issuetype.name,
        "priority": issue.fields.priority.name if issue.fields.priority else "None",
    }


if __name__ == "__main__":
    ticket = get_jira_ticket()
    print(f"Ticket: {ticket['id']}")
    print(f"Summary: {ticket['summary']}")
    print(f"Status: {ticket['status']}")
    print(f"Type: {ticket['issue_type']}")
    print(f"Priority: {ticket['priority']}")
    print(f"Description:\n{ticket['description']}")
