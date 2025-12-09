---
description: Trigger an immediate status line refresh
---

# /statusline-refresh

Triggers an immediate status line refresh by generating conversation activity.

## Usage

```bash
/statusline-refresh
```

## When to Use

Use this command after external changes that affect the status line:

- Git operations (branch switches, commits)
- Worktree switches
- External file modifications

The command exploits Claude Code's automatic 300ms refresh mechanism by generating minimal conversation activity.

---

## Agent Instructions

Output the following message to trigger the status line refresh:

```
🔄 Status line refreshed
```

Do not include timestamps or additional context. The minimal output is intentional to avoid cluttering the conversation.
