# Jira2PR — Claude Code Operator Instructions

This file defines how Claude Code behaves in this project.
Follow these instructions for every user interaction. No Python scripts are needed.

---

## Trigger: Jira Ticket ID

When the user sends a message matching **`[A-Z]+-[0-9]+`** (e.g. `SCRUM-5`, `PROJ-123`, `BUG-42`),
treat it as a Jira ticket ID and execute the full pipeline below.
Extract the ticket ID from longer messages if needed. Begin immediately — no clarification needed.

---

## Safety Check (run BEFORE any action)

Scan the ticket ID and any user-provided description for destructive intent.
Keywords to watch for: "remove", "delete", "drop", "clear", "wipe", "reset", "disable",
"replace" — applied to existing features, files, or functionality.

If detected, stop and ask:

```
⚠️  This ticket appears to involve removing or significantly altering existing functionality:
    "<ticket ID>"

    Proceeding will make potentially irreversible changes to the app.
    Are you sure you want to continue? [y/n]
```

- `y` → proceed to Step 1
- `n` → say "Operation cancelled. No changes were made." and stop

Do NOT read any files, call any API, or run any command until the user confirms.

---

## Pipeline

### Step 1 — Load credentials from .env

Run:
```bash
export $(grep -v '^#' .env | xargs)
```

This loads: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `GITHUB_TOKEN`,
`GITHUB_REPO`, `GITHUB_BASE_BRANCH` (defaults to `main` if unset).

**Never print, log, or display any credential value.**

---

### Step 2 — Fetch Jira ticket

Run:
```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/2/issue/<TICKET_ID>"
```

Parse the JSON response and extract:
- `key` → ticket ID
- `fields.summary` → one-line title
- `fields.description` → full description (may be null — treat as empty string)
- `fields.status.name` → current status
- `fields.issuetype.name` → issue type
- `fields.priority.name` → priority (may be null — treat as "None")

If the response contains an error or HTTP status is not 200, show the error and stop:
- 401 → "Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN in .env"
- 404 → "Ticket <ID> not found. Check the ticket ID and JIRA_URL in .env"

Display to the user:
```
Ticket   : <ID>
Summary  : <summary>
Status   : <status>
Type     : <type> | Priority: <priority>
```

---

### Step 3 — Implement code changes (Claude generates directly)

Read every file in the `app/` directory using the Read tool.

Using the ticket summary and description as the requirement:
- Use the **Edit tool** to modify existing files
- Use the **Write tool** to create new files
- Only touch files that are necessary for the ticket
- Make complete, working changes — not partial diffs

After making all changes, list every modified file:
```
Files changed:
- app/index.html
- app/style.css
```

Display the full content of each changed file in a labelled fenced code block with
the appropriate language tag (html, css, js).

---

### Step 4 — Run tests

Run:
```bash
npm test
```

Show the **complete output verbatim** — do not summarise or truncate.
After the output say: `"Tests complete. Review the results above before confirming the PR."`

If `npm` is not available (exit code 127), say:
`"npm not available — skipping tests."` and continue to Step 5.

---

### Step 5 — Propose PR metadata and ask user

Generate:
- **Branch name**: `feature/<ticket-id-lower>-<short-slug>` (e.g. `feature/scrum-7-add-header`)
  - Use only lowercase letters, numbers, hyphens
  - Keep the slug under 30 chars
- **PR title**: `<TICKET_ID>: <summary>` (max 72 chars)
- **PR description** (markdown):
  ```
  ## Summary
  <1-3 bullet points of what was done>

  ## Motivation
  <why this change was needed, based on the ticket>

  ## Changes
  <bullet list of files changed and what changed in each>
  ```

Show the branch name and PR title to the user, then ask:
```
Create PR? [y/n]
```

- `y` (or starts with y/Y) → proceed to Step 6
- Anything else → say:
  `"Aborted. Your changes are still on disk in app/. To discard them run: git checkout app/"`
  and stop.

---

### Step 6 — Commit, push, and create PR

Run git commands in sequence:
```bash
BASE_BRANCH="${GITHUB_BASE_BRANCH:-main}"

git checkout "$BASE_BRANCH"
git pull origin "$BASE_BRANCH"
git checkout -b "<BRANCH_NAME>"
git add app/
git commit -m "<TICKET_ID>: <summary>"
git push origin "<BRANCH_NAME>"
```

Then create the PR. Try `gh` CLI first:
```bash
gh pr create \
  --title "<PR_TITLE>" \
  --body "<PR_DESCRIPTION>" \
  --base "$BASE_BRANCH" \
  --head "<BRANCH_NAME>"
```

If `gh` is not available, fall back to the GitHub REST API:
```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$GITHUB_REPO/pulls" \
  -d "{\"title\":\"<PR_TITLE>\",\"body\":\"<PR_BODY_ESCAPED>\",\"head\":\"<BRANCH_NAME>\",\"base\":\"$BASE_BRANCH\"}"
```

Extract `html_url` from the JSON response and report:
```
PR created successfully!
<URL>
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Jira 401 | "Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN in .env" |
| Jira 404 | "Ticket <ID> not found. Check the ticket ID and JIRA_URL in .env" |
| `git push` fails | Show the git error. Say: "Push failed. Check your GITHUB_TOKEN and repo permissions." |
| `gh pr create` fails | Try the curl fallback. If that also fails, show the error and stop. |
| No `gh` or `curl` | "Branch pushed. Create the PR manually at github.com/<GITHUB_REPO>/compare/<BRANCH_NAME>" |
| No files changed | "No changes were needed for <TICKET_ID>." and stop. |

Do NOT attempt to auto-fix errors. Report and stop.

---

## Rules

1. **Never read, display, or log `.env` contents or any credential value.**
2. **Never run `python main.py`** — Python scripts are not part of this workflow.
3. **Only stage `app/`** — never commit files outside the `app/` directory.
4. **Never ask for credentials** — they are in `.env` and loaded in Step 1.
5. **Always run the safety check first** for any ticket with destructive keywords.
6. **Never skip tests** unless `npm` is genuinely unavailable (exit code 127).
7. **Default base branch to `main`** if `GITHUB_BASE_BRANCH` is not set.

---

## Project Layout (reference)

```
Jira2PR/
  app/                   # application source files — all Claude changes go here
    index.html
    style.css
    app.js
    buttons.js
  tests/todo.test.js     # Jest test suite
  .env                   # credentials — never read or display contents
  CLAUDE.md              # this file
  main.py                # legacy Python pipeline (not used in this workflow)
```
