---
title: Auto-Execution Pattern for CLI Commands
read_when:
  - "implementing CLI commands that should trigger follow-up actions"
  - "deciding between slash commands vs automatic continuation"
  - "outputting instructions for Claude to follow"
  - "designing post-command workflows"
---

# Auto-Execution Pattern for CLI Commands

CLI commands can output instructions that Claude automatically follows within the same session, eliminating the need for manual user intervention or separate slash commands.

## Pattern Overview

```
┌─────────────────┐
│  CLI Command    │
│   Executes      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Output includes │
│ "Now read and   │
│ execute X"      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Claude reads    │
│ output, follows │
│ instruction     │
└─────────────────┘
```

## When to Use

Use the auto-execution pattern when:

- A follow-up action is **always** appropriate after the command
- The action is **non-destructive** and low-risk
- The user would **always** want this to happen next
- The instruction is a natural continuation of the workflow

## When NOT to Use

Do **not** use auto-execution when:

- The action is **destructive** (deletions, force pushes)
- **User choice** is required (multiple valid options)
- The action might **conflict** with user intent
- The action is **expensive** (time, API calls, cost)
- The action should be **opt-in**

For these cases, use slash commands or explicit user prompts instead.

## Implementation Pattern

Output a clear, imperative instruction that Claude will follow:

```python
# In CLI command output
if hook_path.exists():
    user_output(
        click.style("📋 Post-init hook detected.", fg="cyan")
        + f" Now read and execute {hook_path.relative_to(repo_root)}"
    )
```

### Key Characteristics of Good Instructions

1. **Imperative mood**: "Now read and execute X" not "You might want to consider X"
2. **Specific target**: Point to exact file or action
3. **Single action**: One clear thing to do, not a list of options
4. **Context-appropriate**: Makes sense given what just happened

## Example: Post-Init Hook

The `erk init` command uses this pattern:

```
✓ Initialization complete!

📋 Post-init hook detected. Now read and execute .erk/prompt-hooks/post-init.md
```

Claude sees this output and automatically:

1. Reads the hook file
2. Follows the instructions within it

This replaces what would have been a manual workflow:

1. User runs `erk init`
2. User remembers to run `/erk:post-init`
3. Claude executes the hook

## Comparison: Auto-Execution vs Slash Commands

| Aspect              | Auto-Execution              | Slash Command           |
| ------------------- | --------------------------- | ----------------------- |
| User intervention   | None required               | User must invoke        |
| Discoverability     | Hidden (happens implicitly) | Explicit (user chooses) |
| Control             | Less user control           | Full user control       |
| Workflow continuity | Seamless                    | Interrupted             |
| Good for            | Expected follow-ups         | Optional actions        |
| Bad for             | Destructive/risky actions   | Always-wanted actions   |

## Why This Works

Claude processes the full session context, including command output. When output contains a clear actionable instruction:

1. Claude sees the instruction in the command output
2. Claude recognizes it as an action to take
3. Claude executes the action within the same conversation turn

This is different from how shell commands work (they don't influence the next action) because Claude understands natural language instructions embedded in output.

## Related Documentation

- [Prompt Hooks Guide](../hooks/prompt-hooks.md) - The hook files that auto-execution triggers
- [Fast Path Pattern](fast-path-pattern.md) - Another pattern for optimizing command workflows
