---
description: Prepare local branch for PR submission (squash + commit message, no push)
---

# Prepare Local Branch for PR

Prepares a local branch for PR submission by squashing commits and generating a commit message. Does NOT push or submit - lets you review before pushing.

**Use case:** When you want to prepare your branch with a clean commit message, then push yourself with `gt submit -f`.

## Usage

```bash
/gt:prepare-local
```

## What This Command Does

1. **Squash commits** idempotently (skips if already single commit)
2. **Generate commit message** from PR body (if PR exists) OR AI (if no PR)
3. **Amend commit** with the message

After running, use `gt submit -f` to push the exact local state.

## Implementation

### Step 1: Squash Commits

Run the idempotent squash command:

```bash
dot-agent run gt idempotent-squash 2>&1
```

This command:

- Squashes all commits on the branch into one (if multiple)
- Skips if already a single commit (idempotent)
- Returns JSON with `success`, `squashed`, `commit_count`

Display the output to the user, then parse the JSON from the end.

If squash fails, display error and stop.

### Step 2: Try to Get PR Body

**Session ID extraction**: Look for the `SESSION_CONTEXT` reminder in your context (injected by hooks). It contains `session_id=<uuid>`. Extract this value.

Try to get the commit message from the PR body:

```bash
dot-agent run gt get-pr-commit-message --session-id "<session-id>" 2>&1
```

Parse the JSON output:

- If `success: true`: Use the `message_file` path - PR body is available
- If `success: false` with `error: "no_pr"`: Fall back to AI generation (Step 3)
- Other errors: Display and stop

### Step 3: AI Generation Fallback (only if no PR)

If no PR exists, generate a commit message via AI:

1. **Get the diff** by running pr-prep:

```bash
dot-agent run gt pr-prep --session-id "<session-id>" 2>&1
```

This extracts the diff to a file. Parse the JSON to get `diff_file`.

2. **Generate commit message** using the Task tool:

```
Task(
    subagent_type="commit-message-generator",
    description="Generate commit message from diff",
    prompt="Analyze the git diff and generate a commit message.

Diff file: {diff_file}
Repository root: {repo_root}
Current branch: {current_branch}
Parent branch: {parent_branch}

Use the Read tool to load the diff file."
)
```

3. **Write message to scratch file**:

Use the Write tool to write the generated message to `.erk/scratch/<session-id>/commit-message.txt`.

Set `message_file` to this path.

### Step 4: Amend Commit

Amend the commit with the message file:

```bash
git commit --amend -F "<message_file>"
```

### Step 5: Report Results

Display:

```
✓ Branch prepared for submission
  Message source: [PR body | AI-generated]

Next steps:
  - Review: git log -1
  - Edit:   git commit --amend
  - Push:   gt submit -f
```

## Error Handling

### Squash Errors

If idempotent-squash returns `success: false`:

- Display the error message
- Stop execution

### PR Body Errors

| Error   | Action                     |
| ------- | -------------------------- |
| `no_pr` | Fall back to AI generation |
| Other   | Display error and stop     |

### AI Generation Errors

If pr-prep or Task fails:

- Display error and stop

### Amend Errors

If git commit --amend fails:

- Display error and stop
- User can resolve manually

## Output Format

Structure your output clearly:

**When PR exists:**

```
🔧 Preparing branch locally...

   ⚙️  Running idempotent-squash
   ✓ Already a single commit

   ⚙️  Checking for PR body...
   ✓ Found PR - using PR body for commit message

   ⚙️  Amending commit with PR body
   ✓ Commit amended

✓ Branch prepared for submission
  Message source: PR body

Next steps:
  - Review: git log -1
  - Edit:   git commit --amend
  - Push:   gt submit -f
```

**When no PR (AI-generated):**

```
🔧 Preparing branch locally...

   ⚙️  Running idempotent-squash
   ✓ Squashed 3 commits into 1

   ⚙️  Checking for PR body...
   ℹ No PR found - generating message via AI

   ⚙️  Extracting diff for AI analysis
   ⚙️  Generating commit message...
   ✓ AI-generated commit message

   ⚙️  Amending commit
   ✓ Commit amended

✓ Branch prepared for submission
  Message source: AI-generated

Next steps:
  - Review: git log -1
  - Edit:   git commit --amend
  - Push:   gt submit -f
```
