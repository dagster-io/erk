---
description: Create git commit and submit current branch with Graphite (squashes commits and rebases stack)
argument-hint: <description>
---

# Submit PR

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

**Note:** This command squashes commits and rebases the stack. If you prefer a simpler workflow that preserves your commit history, use `/git:pr-push` instead.

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/gt:pr-submit "Add user authentication feature"

# Without argument (will analyze changes automatically)
/gt:pr-submit
```

## What This Command Does

Executes the complete submit-branch workflow in 3 phases:

1. **Preflight** (Python CLI): Auth checks, squash commits, submit to Graphite, get PR diff
2. **AI Summarization** (Task tool): Generate PR title and body using commit-message-generator subagent
3. **Finalize** (Python CLI): Update PR metadata with AI-generated content

## Implementation

### Step 1: Run Preflight Phase

Execute the preflight command to do all deterministic work.

**Session ID extraction**: Look for the `SESSION_CONTEXT` reminder in your context (injected by hooks). It contains `session_id=<uuid>`. Extract this value and pass it to preflight.

```bash
# Extract session_id from SESSION_CONTEXT reminder and pass to preflight:
dot-agent run gt pr-submit preflight --session-id "<session-id>" 2>&1
```

The `--session-id` is **required**. The diff file is written to `.erk/scratch/<session-id>/` in the repo root, which is accessible to subagents without permission prompts.

**IMPORTANT**: The `2>&1` redirection combines stderr and stdout so progress messages are visible. Display the full command output to the user first (this shows real-time progress), then extract and parse the JSON object from the end of the output.

This returns JSON with:

- `success`: boolean
- `pr_number`: int
- `pr_url`: string
- `graphite_url`: string
- `branch_name`: string
- `diff_file`: path to temp diff file
- `repo_root`: repository root path
- `current_branch`: current branch name
- `parent_branch`: parent branch name
- `issue_number`: int or null
- `message`: status message

If `success` is `false`, display the error and stop.

### Step 2: Generate PR Description via AI

Use the Task tool to delegate to the commit-message-generator agent:

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

Parse the agent output:

- First line = PR title
- Remaining lines = PR body

### Step 3: Run Finalize Phase

Execute the finalize command to update PR metadata.

**IMPORTANT**: Use `--pr-body-file` instead of `--pr-body` to avoid shell escaping issues with multi-line content and special characters.

1. Write the PR body to the scratch directory using the **same session-id directory** where the diff file was written
2. Pass the file path to finalize

**Path construction**: The scratch directory is at `{repo_root}/.erk/scratch/<session-id>/`. The `diff_file` from preflight is already in this directory, so write `pr-body.txt` next to it. For example:

- `diff_file` = `/path/to/repo/.erk/scratch/abc123/pr-diff-70363560.diff`
- Write body to = `/path/to/repo/.erk/scratch/abc123/pr-body.txt`

**NEVER use `/tmp/` for scratch files.** Always use the worktree-local `.erk/scratch/<session-id>/` directory.

```bash
# Write PR body to scratch file first (using Write tool)
# Use the same directory as diff_file from preflight
# Then run finalize with the file path:
dot-agent run gt pr-submit finalize \
    --pr-number {pr_number} \
    --pr-title "{pr_title}" \
    --pr-body-file "{repo_root}/.erk/scratch/<session-id>/pr-body.txt" \
    --diff-file "{diff_file}" 2>&1
```

**Alternative** (for simple, single-line PR bodies without special characters):

```bash
dot-agent run gt pr-submit finalize \
    --pr-number {pr_number} \
    --pr-title "{pr_title}" \
    --pr-body "{pr_body}" \
    --diff-file "{diff_file}" 2>&1
```

### Step 4: Validate PR Rules

Run the PR check command to validate the PR was created correctly:

```bash
erk pr check
```

This validates:

- Issue closing reference (Closes #N) is present when `.impl/issue.json` exists
- PR body contains the standard checkout footer

If any checks fail, display the output and warn the user, but continue to Step 5.

### Step 5: Report Results

Display:

- PR URL: `{pr_url}`
- Graphite URL: `{graphite_url}`
- Success message

## Error Handling

### Preflight Errors - CRITICAL

**When preflight returns `success: false`, IMMEDIATELY ABORT the entire command.** Do NOT attempt to auto-resolve any preflight errors. Display the error clearly and let the user fix it manually.

Display format for ALL preflight failures:

```
❌ PR submission failed: {error_type}

{message}

Error details:
{details as formatted JSON or bullet points}
```

**Do NOT:**

- Try to run `gt sync`, `gt restack`, or any recovery commands
- Attempt to fix merge conflicts automatically
- Continue to the AI summarization step
- Suggest running additional commands in the same session

**DO:**

- Display the error message from the JSON response
- Include the `error_type` and `details` fields
- Stop execution immediately
- Let the user resolve the issue and re-run `/gt:pr-submit`

#### Common Error Types

| Error Type                             | Cause                                                                                                                            |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `submit_merged_parent`                 | Parent branch merged but not in local trunk. User needs to run `gt sync --force`, `gt track --parent master`, then `gt restack`. |
| `gt_not_authenticated`                 | Not logged into Graphite CLI                                                                                                     |
| `gh_not_authenticated`                 | Not logged into GitHub CLI                                                                                                       |
| `no_branch` / `no_parent`              | Not on a valid Graphite branch                                                                                                   |
| `no_commits`                           | No commits to submit                                                                                                             |
| `squash_conflict` / `pr_has_conflicts` | Merge conflicts need manual resolution                                                                                           |
| `submit_failed` / `submit_timeout`     | Graphite submission failed                                                                                                       |

### AI Errors

- Invalid output (missing marker): Fall back to branch name as title
- Task tool failure: Report error and stop

### Finalize Errors

- `pr_update_failed`: Non-fatal, PR was already submitted successfully
