import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"


def generate_code_fix(ticket: dict) -> dict:
    """Send a Jira ticket to Claude and get back a code fix with PR details."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are a senior software engineer. Analyze this Jira ticket and provide a concrete code fix.

Ticket ID: {ticket['id']}
Summary: {ticket['summary']}
Type: {ticket['issue_type']}
Priority: {ticket['priority']}
Description:
{ticket['description']}

Respond with:
1. A brief analysis of the problem (2-3 sentences)
2. The code fix (with filename and full code block)
3. A concise PR title (max 72 chars)
4. A PR description (markdown format, explain what changed and why)
5. A git branch name (format: fix/{ticket_id}-short-description)

Structure your response with clear section headers: ANALYSIS, CODE FIX, PR TITLE, PR DESCRIPTION, BRANCH NAME"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    return _parse_response(response_text, ticket["id"])


def _parse_response(text: str, ticket_id: str) -> dict:
    """Parse Claude's structured response into a dict."""
    sections = {
        "analysis": "",
        "code_fix": "",
        "pr_title": "",
        "pr_description": "",
        "branch_name": "",
        "raw": text,
    }

    current_section = None
    lines = text.splitlines()

    for line in lines:
        upper = line.strip().upper()
        if "ANALYSIS" in upper and upper.startswith(("##", "#", "**", "ANALYSIS")):
            current_section = "analysis"
        elif "CODE FIX" in upper and upper.startswith(("##", "#", "**", "CODE FIX")):
            current_section = "code_fix"
        elif "PR TITLE" in upper and upper.startswith(("##", "#", "**", "PR TITLE")):
            current_section = "pr_title"
        elif "PR DESCRIPTION" in upper and upper.startswith(("##", "#", "**", "PR DESCRIPTION")):
            current_section = "pr_description"
        elif "BRANCH NAME" in upper and upper.startswith(("##", "#", "**", "BRANCH NAME")):
            current_section = "branch_name"
        elif current_section:
            sections[current_section] += line + "\n"

    # Clean up
    for key in ("analysis", "code_fix", "pr_title", "pr_description", "branch_name"):
        sections[key] = sections[key].strip()

    # Fallback branch name
    if not sections["branch_name"]:
        sections["branch_name"] = f"fix/{ticket_id.lower()}-automated-fix"

    # Fallback PR title
    if not sections["pr_title"]:
        sections["pr_title"] = f"Fix: {ticket_id} - Automated code fix"

    return sections


if __name__ == "__main__":
    # Quick test with a mock ticket
    mock_ticket = {
        "id": "TEST-001",
        "summary": "NullPointerException in UserService.getUser()",
        "description": "When userId is null, getUser() throws NPE instead of returning an empty Optional.",
        "issue_type": "Bug",
        "priority": "High",
    }
    result = generate_code_fix(mock_ticket)
    print("=== ANALYSIS ===")
    print(result["analysis"])
    print("\n=== PR TITLE ===")
    print(result["pr_title"])
    print("\n=== BRANCH NAME ===")
    print(result["branch_name"])
    print("\n=== CODE FIX ===")
    print(result["code_fix"])
