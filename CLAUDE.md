# Jira2PR — Claude Code Rules & Pipeline

## How this file works
Claude Code automatically reads `CLAUDE.md` from the project root on every session.
These rules override all default Claude behaviour for this project.
**No additional setup is needed.** When you type a Jira ticket ID, the pipeline below runs automatically.

---

## Token Budget

**This session is limited to 20,000 tokens.**

Claude must track cumulative token usage throughout the session. After every pipeline step, estimate the total tokens used so far (input + output across all messages in this session).

- **Below 20,000 tokens**: proceed normally without mentioning the budget.
- **At or above 20,000 tokens**: display the warning below, then **automatically stop the session** — no developer input required:

```
⚠️  Token budget exceeded (20,000 tokens used this session).
    The pipeline has been halted to prevent degraded output.
    Resume by starting a new session and providing the ticket ID again.
```

**No further steps are executed once the 20k threshold is crossed. The session ends immediately.**

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
  6. Post a comment on the Jira ticket with the PR link

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

**If detected, display the warning below and automatically stop — no developer input required:**
```
⚠️  This ticket appears to involve removing or significantly altering existing functionality.
    Ticket : <TICKET_ID>
    Summary: <summary>

    Pipeline halted. To proceed anyway, re-run and prefix your message with CONFIRM:
    Example: CONFIRM SCRUM-42
```

**If the developer prefixes the ticket ID with `CONFIRM` (e.g. `CONFIRM SCRUM-42`), skip the safety check and proceed directly to Step 1.**

Do NOT read files, call APIs, or run commands unless the message starts with `CONFIRM`.

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

## Step 3 — Analyse & show plan

Read every file in `app/` using the **Read tool** — no edits yet.

Using the ticket summary and description, determine:
- Which files need to change and why
- Exactly what changes are needed in each file

Display the plan, then **immediately proceed to Step 4** — no approval prompt here:
```
Affected files:
- app/app.js     — <reason>
- app/style.css  — <reason>
- app/index.html — <reason>

Proposed changes:
- <change 1>
- <change 2>
- <change 3>

Implementing changes...
```

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
| **Tests pass** | Say `"Tests passed. Proceeding to PR creation."` → continue to Step 6 |
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

Show the proposed branch name and PR title, then **immediately proceed to Step 7** — no approval prompt here.

---

## Step 7 — Commit, push, and create PR

**Before running any git command**, do the following:

**A. Count prior Claude commits on this branch** (run after checking out the correct branch in step 3 below):

```bash
PRIOR_CLAUDE_COUNT=$(git log origin/"$BASE_BRANCH"..HEAD \
  --author="Claude Code" \
  --oneline 2>/dev/null | wc -l | tr -d ' ')
PRIOR_WHAT_LINES=$(git log origin/"$BASE_BRANCH"..HEAD \
  --author="Claude Code" \
  --pretty=format:"%b" 2>/dev/null \
  | grep "^What  :" \
  | sed 's/^What  : //')
COMMIT_SEQ_NUM=$((PRIOR_CLAUDE_COUNT + 1))
COMMIT_SEQUENCE="v${COMMIT_SEQ_NUM}"
```

**B. Compose `COMMIT_WHAT`** using these rules:
- `PRIOR_CLAUDE_COUNT` is **0**: write one sentence (max 15 words) describing what was implemented, from the Step 3 plan.
- `PRIOR_CLAUDE_COUNT` is **1+**: write one sentence describing ONLY the incremental change — what is new vs. `PRIOR_WHAT_LINES`. Must NOT repeat or paraphrase anything already there.
- Never copy the Jira summary verbatim. Describe the actual code change in plain English.

**Correct v1/v2 example:**
- v1: `"Added delete button listener and modal HTML to index.html and app.js"`
- v2: `"Fixed modal not dismissing on outside click; added ESC key handler in app.js"`

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

# --- Commit sequence detection ---
PRIOR_CLAUDE_COUNT=$(git log origin/"$BASE_BRANCH"..HEAD \
  --author="Claude Code" \
  --oneline 2>/dev/null | wc -l | tr -d ' ')
PRIOR_WHAT_LINES=$(git log origin/"$BASE_BRANCH"..HEAD \
  --author="Claude Code" \
  --pretty=format:"%b" 2>/dev/null \
  | grep "^What  :" \
  | sed 's/^What  : //')
COMMIT_SEQ_NUM=$((PRIOR_CLAUDE_COUNT + 1))
COMMIT_SEQUENCE="v${COMMIT_SEQ_NUM}"

# COMMIT_WHAT must describe only what is NEW in this commit vs. PRIOR_WHAT_LINES
COMMIT_TYPE="<feat|fix>"          # feat for non-Bug tickets, fix for Bug tickets
COMMIT_TICKET="<TICKET_ID>"
COMMIT_SUMMARY="<summary>"
COMMIT_WHAT="<one-sentence description of what is NEW in this commit — not already in PRIOR_WHAT_LINES>"
COMMIT_FILES=$(git diff --cached --name-only | tr '\n' ',' | sed 's/,$//')

git commit \
  --author="Claude Code <claude-code@anthropic.com>" \
  -m "[Claude] $COMMIT_TYPE($COMMIT_TICKET) $COMMIT_SEQUENCE: $COMMIT_SUMMARY

What  : $COMMIT_WHAT
Files : $COMMIT_FILES
Ticket: $COMMIT_TICKET | Author: Claude (claude-sonnet-4-6)"

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

## Step 8 — Write back to Jira

Run after a successful PR creation. Failures are **non-fatal** — warn and continue.

### Step 8a — Post a comment on the Jira ticket

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_URL/rest/api/2/issue/<TICKET_ID>/comment" \
  -d "{\"body\": \"🤖 PR created by Claude Code\n\nPR     : <PR_URL>\nBranch : <BRANCH_NAME>\nSummary: <COMMIT_SUMMARY>\n\nWhat was implemented:\n<COMMIT_WHAT>\"}"
```

- HTTP 2xx → say `"Jira comment posted."`
- Anything else → say `"Warning: Could not post Jira comment. You can add it manually."` — continue

After posting the comment display:
```
Jira updated ✓
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Jira 401 | Authentication failed message — stop |
| Jira 404 | Ticket not found message — stop |
| Tests fail | `"Tests failed. No PR was created."` — stop |
| `git stash pop` conflict | Show conflict output. Say `"Stash pop failed. Resolve conflicts in app/ manually."` — stop |
| `git push` fails | Show git error. Say `"Push failed. Check GITHUB_TOKEN and repo permissions."` — stop |
| `gh pr create` fails | Try Node.js fallback. If that also fails, show error — stop |
| Neither `gh` nor Node.js | `"Branch pushed. Create the PR manually at github.com/<GITHUB_REPO>/compare/<BRANCH_NAME>"` |
| No files changed | `"No changes were needed for <TICKET_ID>."` — stop |
| Jira comment POST fails | Warn and continue — non-fatal |

Do NOT attempt to auto-fix errors. Report and stop.

---

## Rules

1. **Never read, display, or log `.env` contents or any credential value.**
2. **Never run `python main.py`** — legacy script, not part of this workflow.
3. **Only stage `app/`** — never commit files outside the `app/` directory.
4. **Never ask for credentials** — they live in `.env` and are loaded in Step 1.
5. **Always run the safety check first** — before loading credentials or touching files.
6. **Always show the analysis plan** before editing any file — but proceed automatically (no approval prompt at this step).
7. **Never create a PR if tests fail** — tests are a hard gate.
8. **Always `git stash` before switching branches** — protects Step 4 changes.
9. **Reuse an existing branch** if its name already contains the ticket ID.
10. **Default base branch to `main`** if `GITHUB_BASE_BRANCH` is unset.
11. **Branch prefix = `bugfix/`** for Bug type; `feature/` for all other types.
12. **Never modify the Jira ticket description** — only post comments via `POST /comment`; the `PUT /issue` description endpoint must never be called.
13. **Commit sequence**: Before every commit, count prior Claude commits on the branch with `git log --author="Claude Code"`. Set `COMMIT_SEQUENCE` to `v1`, `v2`, etc. The `COMMIT_WHAT` line must describe only what is new in the current commit — it must not repeat or paraphrase the `What` line from any prior Claude commit on the same branch.
14. **Token budget is a hard stop**: If cumulative session tokens reach 20,000, display the budget warning and halt immediately — no prompt, no developer input required. The developer must start a new session.

---

## Pipeline at a glance

```
Ticket ID received
      │
      ▼
Safety Check ── destructive? ── auto-halt (re-run with CONFIRM <ID> to override)
      │ clear
      ▼
Step 1 · Load .env
      │
      ▼
Step 2 · Fetch Jira → display ticket info
      │
      ▼
Step 3 · Read app/ → analyse → show plan → auto-proceed
      │
      ▼
Step 4 · Implement changes (Edit / Write)
      │
      ▼
Step 5 · npm test
      │ pass                               fail → stop (no PR)
      ▼
Step 6 · Generate branch + PR metadata → auto-proceed
      │
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
      │
      ▼
Step 8 · POST /comment → Jira ticket (PR link + summary)
      │
      ▼
  Done ✓

  [At any step: token usage ≥ 20k → auto-halt, start new session]
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
