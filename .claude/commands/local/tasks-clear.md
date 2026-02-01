---
description: Clear all tasks from the current session
---

# /tasks-clear

Clears all tasks from the current Claude Code session and removes them from the display.

## Usage

```bash
/tasks-clear
```

## When to Use

Use this command to clear the task list in these scenarios:

- After completing all tasks in the current session
- When starting fresh on a new set of tasks
- When cleaning up abandoned or obsolete tasks
- When the task list has become cluttered or irrelevant

---

## Agent Instructions

Clear all tasks by following these steps:

1. Use the TaskList tool to get all current tasks
2. For each task returned, use TaskUpdate with `status: "deleted"` to remove it
3. After clearing, output a brief confirmation:

```
All tasks cleared.
```

Keep the output minimal and clean.
