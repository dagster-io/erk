---
description: Clear all todos from the current session
---

# /todos-clear

Clears all todo items from the current Claude Code session.

## Usage

```bash
/todos-clear
```

## When to Use

Use this command to clear the todo list in these scenarios:

- After completing all tasks in the current session
- When starting fresh on a new set of tasks
- When cleaning up abandoned or obsolete todos
- When the todo list has become cluttered or irrelevant

---

## Agent Instructions

Clear all todos by using the TodoWrite tool with an empty array:

```json
[]
```

After clearing, output a brief confirmation:

```
✅ All todos cleared
```

Keep the output minimal and clean.
