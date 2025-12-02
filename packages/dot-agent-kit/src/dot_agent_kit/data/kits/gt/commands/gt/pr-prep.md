---
description: Prepare branch for PR (squash + AI commit message, no push)
---

# Prepare Branch for PR

Squashes commits, generates AI commit message, and amends the commit. Does NOT push or submit to GitHub - lets you review and edit the commit message before pushing.

**Use case:** When you want to prepare your commit message without immediately submitting the PR.

## Usage

```bash
/gt:pr-prep
```

## What This Command Does

Prepares your branch for PR submission in 2 phases:

1. **Prep Phase** (Python CLI): Auth checks, restack conflict detection, squash commits, extract diff
2. **AI Message Generation** (Task tool): Generate commit message using commit-message-generator subagent

The commit is amended with the AI-generated message, but NOT pushed. You can then:

- Review: `git log -1`
- Edit: `git commit --amend`
- Push: `gt submit --publish`

## Implementation

### Step 1: Run Prep Phase (Kit CLI)

Execute the prep command to do all deterministic work.

**Session ID extraction**: Look for the `SESSION_CONTEXT` reminder in your context (injected by hooks). It contains `session_id=<uuid>`. Extract this value and pass it to prep.

```bash
# Extract session_id from SESSION_CONTEXT reminder and pass to prep:
dot-agent run gt pr-prep --session-id "<session-id>" 2>&1
```

The `--session-id` is **required**. The diff file is written to `.erk/scratch/<session-id>/` in the repo root, which is accessible to subagents without permission prompts.

**IMPORTANT**: The `2>&1` redirection combines stderr and stdout so progress messages are visible. Display the full command output to the user first (this shows real-time progress), then extract and parse the JSON object from the end of the output.

This returns JSON with:

- `success`: boolean
- `diff_file`: path to diff file
- `repo_root`: repository root path
- `current_branch`: current branch name
- `parent_branch`: parent branch name
- `commit_count`: int
- `squashed`: boolean
- `message`: status message

If `success` is `false`, handle the error (see Error Handling section below).

### Step 2: Generate Commit Message via AI

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

- First line = commit title
- Remaining lines = commit body

### Step 3: Amend Commit

Combine the title and body into a single commit message, then amend the current commit.

**IMPORTANT**: Use a heredoc or scratch file to avoid shell escaping issues with multi-line content.

```bash
# Write commit message to scratch file first
# Using Write tool: write message to .erk/scratch/<session-id>/commit-msg.txt

# Then amend with the file:
git commit --amend -F ".erk/scratch/<session-id>/commit-msg.txt"
```

### Step 4: Report Results

Display:

```
✓ Branch prepared for submission
  Commit message updated with AI-generated summary

Next steps:
  - Review: git log -1
  - Edit:   git commit --amend
  - Push:   gt submit --publish
```

## Error Handling

### Prep Phase Errors - CRITICAL

**When prep returns `success: false` with `error_type: "restack_conflict"`, IMMEDIATELY ABORT.** Do NOT attempt to auto-resolve restack conflicts.

Display format:

```
❌ Restack conflicts detected

Run 'gt restack' to resolve conflicts first, then re-run /gt:pr-prep
```

**Do NOT:**

- Try to run `gt restack` automatically
- Attempt to fix merge conflicts
- Continue to the AI message generation step

**DO:**

- Display the error message clearly
- Stop execution immediately
- Let the user resolve conflicts manually

#### Error Types

| Error Type             | Cause                                   | User Action                               |
| ---------------------- | --------------------------------------- | ----------------------------------------- |
| `restack_conflict`     | Conflicts detected during restack check | Run `gt restack` to resolve, then retry   |
| `squash_conflict`      | Conflicts detected during squash        | Resolve conflicts manually, then retry    |
| `gt_not_authenticated` | Not logged into Graphite CLI            | Run `gt auth`                             |
| `gh_not_authenticated` | Not logged into GitHub CLI              | Run `gh auth login`                       |
| `no_branch`            | Not on a valid branch                   | Switch to a valid branch                  |
| `no_parent`            | Cannot determine parent branch          | Ensure branch has parent (use `gt track`) |
| `no_commits`           | No commits to prepare                   | Make commits first                        |
| `squash_failed`        | Failed to squash commits                | Check git status and resolve issues       |

### AI Errors

- Invalid output: Fall back to branch name as title
- Task tool failure: Report error and stop

### Amend Errors

- If git commit --amend fails: Display error and stop
- User can manually edit and re-run command
