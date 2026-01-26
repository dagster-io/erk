---
description: Submit the last created issue for remote implementation
---

# /erk:plan-submit

## Goal

Find the most recent GitHub issue created in this conversation and submit it for remote AI implementation via `erk plan submit`.

## What This Command Does

1. Search conversation for the last GitHub issue reference
2. Extract the issue number
3. Run `erk plan submit <issue_number>` to trigger remote implementation

## Finding the Issue

Search the conversation from bottom to top for these patterns (in priority order):

1. **plan-save/save-raw-plan output**: Look for `**Issue:** https://github.com/.../issues/<number>`
2. **Issue URL**: `https://github.com/<owner>/<repo>/issues/<number>`

Extract the issue number from the most recent match.

## Execution

Once you have the issue number, run:

```bash
erk plan submit <issue_number>
```

Display the command output to the user. The `erk plan submit` command handles all validation (issue existence, labels, state).

## Local Execution

For local development and faster iteration, you can run implementations locally instead of GitHub Actions:

```bash
erk plan submit --local <issue_number>
```

**Prerequisites:**
1. Create `~/.erk/local-runner-config.toml` with credentials (see `.erk/local-runner-config.toml.example`)
2. Install tmux: `brew install tmux` (macOS) or `apt install tmux` (Linux)

**Monitoring:**
- View active runs: `erk local-runner status`
- Attach to session: `erk local-runner logs <issue_number>`
- Stop implementation: `erk local-runner stop <issue_number>`

**Benefits:**
- Faster iteration (no GitHub Actions queue)
- Live debugging via tmux attach
- Full control over execution environment

**Limitations:**
- No resource limits (uses host CPU/memory)
- Manual cleanup of worktrees
- Credentials stored locally

## Error Cases

- **No issue found in conversation**: Report "No GitHub issue found in conversation. Run /erk:plan-save first to create an issue."
- **erk plan submit fails**: Display the error output from the command (erk plan submit validates the issue)
