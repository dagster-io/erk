---
description: Sync PR title and body from the latest git commit message
---

# /pr-sync-commit

Updates the current PR's title and body from the latest git commit message, preserving any existing header (plan links) and footer (closing references, checkout instructions, workflow run links).

## Usage

```bash
/local:pr-sync-commit
```

## When to Use

Use this command when:

- You've amended or updated the commit message and want the PR to match
- The PR title/body is out of sync with the current commit
- You want to quickly sync PR metadata after rebasing

---

## Agent Instructions

Run the exec command:

```bash
erk exec pr-sync-commit
```

The command will:

1. Get the current branch and find its associated PR
2. Get the HEAD commit message (title and body)
3. Extract and preserve any header (`**Plan:** #N`, `**Remotely executed:**`)
4. Extract and preserve any footer (`Closes #N`, checkout instructions)
5. Update the PR with the new title and rebuilt body
6. Output a summary of what was preserved

Report the output to the user.
