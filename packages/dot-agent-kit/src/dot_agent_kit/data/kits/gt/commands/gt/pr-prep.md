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

## Implementation

This command delegates to `erk pr prepare-local` which handles everything:

- Auth checks
- Squash commits idempotently
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
  - Push:   gt submit --publish
```

## Error Handling

If `erk pr prepare-local` fails, display the error and stop. The Python implementation handles all error cases including:

- Restack conflicts
- Squash conflicts
- Authentication issues
- No commits to prepare

Do NOT attempt to auto-resolve errors. Let the user fix issues and re-run.
