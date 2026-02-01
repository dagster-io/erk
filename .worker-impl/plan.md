# Plan: Rename `/local:todos-clear` to `/local:tasks-clear`

## Changes

1. **Create** `.claude/commands/local/tasks-clear.md` with updated content:
   - Replace all references to "todos" with "tasks"
   - Update the command name from `/todos-clear` to `/tasks-clear`
   - Replace `TodoWrite` tool reference with the appropriate task-clearing approach (likely `TaskUpdate` to delete all tasks, or similar)
   - Update description and instructions accordingly

2. **Delete** `.claude/commands/local/todos-clear.md`

## File: `.claude/commands/local/tasks-clear.md`

Updated prompt will instruct the agent to:
- Use `TaskList` to get all tasks
- Use `TaskUpdate` with `status: "deleted"` for each task
- Output confirmation message

## Verification

- Run `/local:tasks-clear` to confirm it works
- Confirm `/local:todos-clear` no longer exists