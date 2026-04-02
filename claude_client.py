import os
import re

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"
APP_DIR = "app"


def read_app_files() -> dict[str, str]:
    """Return a dict of {filename: content} for every readable file in app/."""
    files = {}
    for name in sorted(os.listdir(APP_DIR)):
        path = os.path.join(APP_DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                files[name] = f.read()
        except (UnicodeDecodeError, IOError):
            pass  # skip binary/unreadable files
    return files


def generate_code_fix(ticket: dict) -> dict:
    """Use Claude (with tool use) to implement the Jira ticket changes in the app files.

    Returns a dict with keys:
        changed_files  – {filename: new_content} for every file Claude modified
        pr_title       – suggested PR title
        pr_description – markdown PR body derived from the Jira ticket
        branch_name    – suggested git branch name
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    app_files = read_app_files()
    files_context = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in app_files.items()
    )

    tools = [
        {
            "name": "write_file",
            "description": (
                "Write or update a file in the app/ directory. "
                "Call this for every file that must be created or modified."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename relative to app/ (e.g. 'index.html')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Complete new content of the file",
                    },
                },
                "required": ["filename", "content"],
            },
        }
    ]

    system_prompt = (
        "You are a skilled web developer working on a plain HTML/CSS/JavaScript Todo application. "
        "You will receive a Jira ticket and the current source files. "
        "Implement ALL changes described in the ticket by calling write_file for every file "
        "that must be created or modified. Return complete file contents, not diffs. "
        "Only touch files that are necessary."
    )

    user_message = (
        f"Jira Ticket: {ticket['id']}\n"
        f"Summary: {ticket['summary']}\n"
        f"Type: {ticket['issue_type']}\n"
        f"Priority: {ticket['priority']}\n\n"
        f"Description:\n{ticket['description']}\n\n"
        f"Current app files:\n{files_context}\n\n"
        "Implement the changes described above by calling write_file for each file that needs to change."
    )

    messages = [{"role": "user", "content": user_message}]
    changed_files: dict[str, str] = {}

    # Agentic loop — keep going until Claude stops using tools
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        tool_calls = [b for b in response.content if b.type == "tool_use"]

        if not tool_calls:
            break

        tool_results = []
        for call in tool_calls:
            if call.name == "write_file":
                filename = call.input["filename"]
                content = call.input["content"]
                changed_files[filename] = content
                print(f"  [Claude] write_file → {filename}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": f"File '{filename}' written successfully.",
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            break

    # Generate PR metadata in a separate, focused call
    meta = _generate_pr_metadata(client, ticket, changed_files)

    return {
        "changed_files": changed_files,
        "pr_title": meta["pr_title"],
        "pr_description": meta["pr_description"],
        "branch_name": meta["branch_name"],
    }


def _generate_pr_metadata(client: anthropic.Anthropic, ticket: dict, changed_files: dict) -> dict:
    """Ask Claude for a PR title, description, and branch name."""
    changed_list = ", ".join(changed_files.keys()) if changed_files else "no files changed"

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Based on the Jira ticket below, generate:\n"
                    "1. A concise PR title (≤72 chars, include the ticket ID)\n"
                    "2. A markdown PR description with sections: ## Summary, ## Motivation, ## Changes\n"
                    "3. A git branch name in the format: feature/{ticket_id_lower}-short-slug\n\n"
                    f"Ticket ID: {ticket['id']}\n"
                    f"Summary: {ticket['summary']}\n"
                    f"Type: {ticket['issue_type']} | Priority: {ticket['priority']}\n\n"
                    f"Description:\n{ticket['description']}\n\n"
                    f"Files changed: {changed_list}\n\n"
                    "Reply with exactly three sections labelled:\n"
                    "PR TITLE:\n"
                    "PR DESCRIPTION:\n"
                    "BRANCH NAME:"
                ).format(ticket_id_lower=ticket["id"].lower()),
            }
        ],
    )

    text = response.content[0].text
    return _parse_metadata(text, ticket["id"])


def _parse_metadata(text: str, ticket_id: str) -> dict:
    """Parse the metadata reply from Claude."""
    result = {"pr_title": "", "pr_description": "", "branch_name": ""}
    current = None
    buf: list[str] = []

    def flush():
        if current:
            result[current] = "\n".join(buf).strip()
        buf.clear()

    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("PR TITLE:"):
            flush()
            current = "pr_title"
            rest = stripped[len("PR TITLE:"):].strip()
            buf = [rest] if rest else []
        elif upper.startswith("PR DESCRIPTION:"):
            flush()
            current = "pr_description"
            rest = stripped[len("PR DESCRIPTION:"):].strip()
            buf = [rest] if rest else []
        elif upper.startswith("BRANCH NAME:"):
            flush()
            current = "branch_name"
            rest = stripped[len("BRANCH NAME:"):].strip()
            buf = [rest] if rest else []
        else:
            if current:
                buf.append(line)

    flush()

    # Fallbacks
    if not result["branch_name"]:
        result["branch_name"] = f"feature/{ticket_id.lower()}-automated"
    if not result["pr_title"]:
        result["pr_title"] = f"{ticket_id}: Automated fix"

    # Sanitise branch name
    result["branch_name"] = re.sub(r"[^a-zA-Z0-9/_-]", "-", result["branch_name"]).strip("-")

    return result


if __name__ == "__main__":
    from jira_client import get_jira_ticket

    ticket = get_jira_ticket()
    result = generate_code_fix(ticket)
    print("=== PR TITLE ===")
    print(result["pr_title"])
    print("\n=== BRANCH NAME ===")
    print(result["branch_name"])
    print("\n=== CHANGED FILES ===")
    for f in result["changed_files"]:
        print(f"  {f}")
    print("\n=== PR DESCRIPTION ===")
    print(result["pr_description"])
