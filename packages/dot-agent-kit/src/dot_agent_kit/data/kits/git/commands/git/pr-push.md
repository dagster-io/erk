---
description: Create git commit and push branch as PR using git + GitHub CLI
argument-hint: <description>
---

# Push PR (Git Only)

Automatically create a git commit with a helpful summary message and push the current branch as a pull request using standard git + GitHub CLI (no Graphite required).

**Note:** This command uses git-only workflows without Graphite. For Graphite-based submission with stack management, use `/gt:pr-submit` instead.

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/git:pr-push "Add user authentication feature"

# Without argument (will analyze changes automatically)
/git:pr-push
```

## Implementation

This command delegates to `erk pr push` which handles everything:

- Preflight checks (auth, stage changes, push, create PR)
- AI-powered commit message generation
- PR metadata update with title and body
- PR validation

### Execute

Run the full push workflow:

```bash
erk pr push
```

### Report Results

The command outputs:

- PR URL
- Success message

After completion, suggest:

```
Create insight extraction plan to improve docs/agent (optional):
    /erk:create-extraction-plan
```

## Error Handling

If `erk pr push` fails, display the error and stop. The Python implementation handles all error cases including:

- Authentication issues (GitHub)
- Push failures (diverged branches)
- PR creation failures

Do NOT attempt to auto-resolve errors. Let the user fix issues and re-run.
