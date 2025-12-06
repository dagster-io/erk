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

## Implementation

This command delegates to `erk pr prepare-local` which handles everything:

- Squash commits idempotently (skips if already single commit)
- Get commit message from PR body (if PR exists) OR generate via AI
- Amend commit with the message

### Execute

Run the prepare-local workflow:

```bash
erk pr prepare-local
```

### Report Results

After completion, suggest next steps:

```
Next steps:
  - Review: git log -1
  - Edit:   git commit --amend
  - Push:   gt submit -f
```

## Error Handling

If `erk pr prepare-local` fails, display the error and stop. The Python implementation handles all error cases including:

- Squash conflicts
- Authentication issues
- No commits to prepare

Do NOT attempt to auto-resolve errors. Let the user fix issues and re-run.
