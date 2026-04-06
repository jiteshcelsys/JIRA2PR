# Jira2PR — Claude Code Rules & Pipeline

## How this file works
Claude Code automatically reads `CLAUDE.md` from the project root on every session.
These rules override all default Claude behaviour for this project.
**No additional setup is needed.** When you type a Jira ticket ID, the pipeline below runs automatically.

---

## Greeting & Onboarding

When the user opens a new session **without** a ticket ID in their first message
(e.g. they say "hi", "hello", "start", "help", or anything else that is not a ticket ID),
respond with exactly this message and wait for their reply:

```
👋 Welcome to Jira2PR!

I'll take a Jira ticket number and automatically:
  1. Fetch the ticket details from Jira
  2. Analyse the code and propose a plan for your approval
  3. Implement the changes
  4. Run tests
  5. Create a GitHub pull request

Please enter your Jira ticket number to get started.
Example: SCRUM-10  |  PROJ-123  |  BUG-42
```

Do not start the pipeline, load credentials, or take any other action until the user
provides a ticket ID.

---

## Trigger

Any message containing a pattern matching **`[A-Z]+-[0-9]+`** (e.g. `SCRUM-10`, `PROJ-123`, `BUG-42`)
is treated as a Jira ticket ID. The full pipeline executes immediately — no clarification needed.

---

## Safety Check (runs before everything else)

Before loading credentials or calling any API, scan the ticket summary and description for
destructive intent. Keywords to watch: `remove`, `delete`, `drop`, `clear`, `wipe`, `reset`,
`disable`, `replace` — when applied to existing features, files, or functionality.

**If detected, stop and prompt:**
```
⚠️  This ticket appears to involve removing or significantly altering existing functionality.
    Ticket : <TICKET_ID>
    Summary: <summary>

    Proceeding will make potentially irreversible changes to the app.
    Are you sure you want to continue? [y/n]
```
- `y` → proceed to Step 1
- `n` → say `"Operation cancelled. No changes were made."` and stop

Do NOT read files, call APIs, or run commands until confirmed.

---

## Step 1 — Load credentials

```bash
export $(grep -v '^#' .env | xargs)
```

Variables loaded:

| Variable             | Purpose                                       |
|----------------------|-----------------------------------------------|
| `JIRA_URL`           | Base URL of the Jira instance                 |
| `JIRA_EMAIL`         | Jira account email                            |
| `JIRA_API_TOKEN`     | Jira API token                                |
| `GITHUB_TOKEN`       | GitHub personal access token                  |
| `GITHUB_REPO`        | `owner/repo` (e.g. `jiteshcelsys/JIRA2PR`)   |
| `GITHUB_BASE_BRANCH` | Target branch — defaults to `main` if unset   |

**Never print, log, or display any credential value.**

---

## Step 2 — Fetch & display the Jira ticket

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_URL/rest/api/2/issue/<TICKET_ID>"
```

Extract from the JSON response:

| JSON field               | Variable      | Notes                        |
|--------------------------|---------------|------------------------------|
| `key`                    | ticket ID     |                              |
| `fields.summary`         | summary       | Used in PR title + commit    |
| `fields.description`     | description   | null → treat as empty string |
| `fields.status.name`     | status        | Display only                 |
| `fields.issuetype.name`  | issue type    | Used for branch prefix       |
| `fields.priority.name`   | priority      | null → "None"                |

**Error handling:**
- HTTP 401 → `"Authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN in .env"` — stop
- HTTP 404 → `"Ticket <ID> not found. Check the ticket ID and JIRA_URL in .env"` — stop

**Display:**
```
Ticket   : <ID>
Summary  : <summary>
Status   : <status>
Type     : <type> | Priority: <priority>
```

---

## Step 3 — Analyse & propose a plan (developer approval required)

Read every file in `app/` using the **Read tool** — no edits yet.

Using the ticket summary and description, determine:
- Which files need to change and why
- Exactly what changes are needed in each file

Present the plan:
```
Affected files:
- app/app.js     — <reason>
- app/style.css  — <reason>
- app/index.html — <reason>

Proposed changes:
- <change 1>
- <change 2>
- <change 3>

Proceed with these changes? [y/n]
```

- `y` → continue to Step 4
- anything else → `"Cancelled. No files were modified."` — stop

**Do NOT edit any file before the developer types `y`.**

---

## Step 4 — Implement code changes

Apply only the changes from the approved plan:
- **Edit tool** to modify existing files
- **Write tool** to create new files
- Only touch files listed in the plan
- Make complete, working changes — no partial diffs

After all edits, display:
```
Files changed:
- app/index.html
- app/style.css
- app/app.js
```

Show the full content of each changed file in a fenced code block with the correct language tag
(`html`, `css`, `js`).

---

## Step 5 — Run tests (gates PR creation)

```bash
npm test
```

Show complete output verbatim — do not truncate.

| Result | Action |
|--------|--------|
| **Tests pass** | Say `"Tests complete. Review the results above before confirming the PR."` → continue to Step 6 |
| **Tests fail** | Say `"Tests failed. Fix the failures above before creating a PR. No PR was created."` → **stop** |
| npm not found (exit 127) | Say `"npm not available — skipping tests."` → continue to Step 6 |

**A PR is never created when tests fail.**

---

## Step 6 — Propose PR metadata and ask developer

**Branch prefix** (from `issuetype` in Step 2):
- `Bug` → `bugfix/`
- Any other type → `feature/`

**Branch name**: `<prefix><ticket-id-lowercase>-<short-slug>`
- Lowercase letters, numbers, hyphens only
- Slug ≤ 30 characters
- Examples: `feature/scrum-10-add-task-popup` · `bugfix/proj-123-null-token`

**PR title**: `<TICKET_ID>: <summary>` (max 72 chars)

**PR description:**
```markdown
## Summary
- <bullet 1>
- <bullet 2>

## Motivation
<why this change was needed, from the ticket>

## Changes
- `app/file.js` — <what changed>

## Tests
- <test name 1>
- <test name 2>

## Jira
[<TICKET_ID>](<JIRA_URL>/browse/<TICKET_ID>)
```

Show the proposed branch name and PR title, then ask:
```
Create PR? [y/n]
```
- `y` → continue to Step 7
- anything else → `"Aborted. Your changes are still on disk in app/. To discard them run: git checkout app/"` — stop

---

## Step 7 — Commit, push, and create PR

Run in this exact sequence:

```bash
BASE_BRANCH="${GITHUB_BASE_BRANCH:-main}"

# 1. Stash the uncommitted changes from Step 4
git stash

# 2. Sync the base branch
git checkout "$BASE_BRANCH"
git pull origin "$BASE_BRANCH"

# 3. Smart branch: reuse existing branch if ticket ID is already in the name, else create new
EXISTING=$(git branch --list "*<TICKET_ID_LOWER>*" | head -1 | xargs)
if [ -n "$EXISTING" ]; then
  git checkout "$EXISTING"
  echo "Reusing existing branch: $EXISTING"
else
  git checkout -b "<BRANCH_NAME>"
  echo "Created new branch: <BRANCH_NAME>"
fi

# 4. Restore the stashed changes onto the correct branch
git stash pop

# 5. Stage only app/, commit, push
git add app/
git commit -m "<TICKET_ID>: <summary>"
git push origin "<BRANCH_NAME>"
```

**Create the PR — try `gh` CLI first:**
```bash
gh pr create \
  --title "<PR_TITLE>" \
  --body "<PR_DESCRIPTION>" \
  --base "$BASE_BRANCH" \
  --head "<BRANCH_NAME>"
```

**If `gh` is not available, fall back to Node.js (always available in this project):**
```bash
node -e "
const https = require('https');
const body = JSON.stringify({
  title: '<PR_TITLE>',
  body: '<PR_DESCRIPTION_ESCAPED>',
  head: '<BRANCH_NAME>',
  base: process.env.GITHUB_BASE_BRANCH || 'main'
});
const options = {
  hostname: 'api.github.com',
  path: '/repos/' + process.env.GITHUB_REPO + '/pulls',
  method: 'POST',
  headers: {
    'Authorization': 'token ' + process.env.GITHUB_TOKEN,
    'Content-Type': 'application/json',
    'User-Agent': 'Jira2PR',
    'Content-Length': Buffer.byteLength(body)
  }
};
const req = https.request(options, res => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const pr = JSON.parse(data);
    console.log(pr.html_url || JSON.stringify(pr));
  });
});
req.write(body);
req.end();
"
```

**On success:**
```
PR created successfully!
<URL>
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Jira 401 | Authentication failed message — stop |
| Jira 404 | Ticket not found message — stop |
| Developer rejects plan | `"Cancelled. No files were modified."` — stop |
| Tests fail | `"Tests failed. No PR was created."` — stop |
| `git stash pop` conflict | Show conflict output. Say `"Stash pop failed. Resolve conflicts in app/ manually."` — stop |
| `git push` fails | Show git error. Say `"Push failed. Check GITHUB_TOKEN and repo permissions."` — stop |
| `gh pr create` fails | Try Node.js fallback. If that also fails, show error — stop |
| Neither `gh` nor Node.js | `"Branch pushed. Create the PR manually at github.com/<GITHUB_REPO>/compare/<BRANCH_NAME>"` |
| No files changed | `"No changes were needed for <TICKET_ID>."` — stop |

Do NOT attempt to auto-fix errors. Report and stop.

---

## Rules

1. **Never read, display, or log `.env` contents or any credential value.**
2. **Never run `python main.py`** — legacy script, not part of this workflow.
3. **Only stage `app/`** — never commit files outside the `app/` directory.
4. **Never ask for credentials** — they live in `.env` and are loaded in Step 1.
5. **Always run the safety check first** — before loading credentials or touching files.
6. **Always show the analysis plan and get `y` approval** before editing any file.
7. **Never create a PR if tests fail** — tests are a hard gate.
8. **Always `git stash` before switching branches** — protects Step 4 changes.
9. **Reuse an existing branch** if its name already contains the ticket ID.
10. **Default base branch to `main`** if `GITHUB_BASE_BRANCH` is unset.
11. **Branch prefix = `bugfix/`** for Bug type; `feature/` for all other types.

---

## Pipeline at a glance

```
Ticket ID received
      │
      ▼
Safety Check ──── destructive? ──► confirm y/n ──► n → stop
      │ clear
      ▼
Step 1 · Load .env
      │
      ▼
Step 2 · Fetch Jira → display ticket info
      │
      ▼
Step 3 · Read app/ → analyse → propose plan → y/n
      │ y                                    n → stop
      ▼
Step 4 · Implement changes (Edit / Write)
      │
      ▼
Step 5 · npm test
      │ pass                               fail → stop (no PR)
      ▼
Step 6 · Generate branch + PR metadata → y/n
      │ y                                    n → stop
      ▼
Step 7 · git stash
         git checkout base + pull
         smart branch (reuse or create)
         git stash pop
         git add app/ + commit + push
         gh pr create  (or Node.js fallback)
      │
      ▼
  PR URL displayed ✓
```

---

## Project layout

```
Jira2PR/
  app/                  ← all Claude edits go here
    index.html
    style.css
    app.js
    buttons.js
  tests/
    todo.test.js        ← Jest suite — must pass before PR
  .env                  ← credentials (never display)
  CLAUDE.md             ← this file — the only rules file
  main.py               ← legacy Python pipeline (never run)
```
