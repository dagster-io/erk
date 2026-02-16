---
title: Claude CLI Execution Modes
read_when:
  - "writing multi-phase slash commands that use context: fork"
  - "understanding why Task tool is required instead of skill invocation"
  - "debugging commands that work interactively but break in --print mode"
tripwires:
  - action: "writing multi-phase commands without testing in --print mode"
    warning: "context: fork creates true isolation in interactive mode but loads inline in --print mode. Use Task tool for guaranteed isolation in all modes."
---

# Claude CLI Execution Modes

Claude Code commands with `context: fork` metadata behave differently depending on the execution mode. This difference has practical consequences for multi-phase commands that need isolation between phases.

## The Behavioral Difference

| Mode        | `context: fork` Behavior                 | Isolation      |
| ----------- | ---------------------------------------- | -------------- |
| Interactive | Creates a fresh subagent context         | True isolation |
| `--print`   | Loads command inline into parent context | No isolation   |

In interactive mode, `context: fork` works as expected — the skill/command runs in a separate agent with its own context. In `--print` mode, the fork metadata is present but the command content is loaded inline, meaning terminal instructions from one phase can contaminate the parent context.

## Task Tool as Guaranteed Isolation

The Task tool creates a subprocess agent regardless of execution mode. This makes it the reliable choice for any command that needs isolation:

```
Task(
  subagent_type: "general-purpose",
  prompt: "Load and follow the skill instructions in .claude/skills/my-skill/SKILL.md ..."
)
```

This pattern wraps a skill invocation inside a Task tool call, ensuring the skill runs in a separate agent even in `--print` mode.

## When Each Pattern Applies

| Scenario                                | Use             | Why                          |
| --------------------------------------- | --------------- | ---------------------------- |
| Read-only analysis in interactive mode  | `context: fork` | Simple, efficient            |
| Multi-phase commands that modify state  | Task tool       | Needs isolation in all modes |
| Commands that must work in both modes   | Task tool       | `--print` safety             |
| Preview-only commands (no side effects) | Either          | No state to contaminate      |

## Worked Example: pr-address vs pr-preview-address

<!-- Source: .claude/commands/erk/pr-address.md -->

`pr-address.md` uses Task tool to invoke the `pr-feedback-classifier` skill because it modifies files based on the classification results. If the classifier's context leaked into the parent, subsequent phases could be contaminated.

<!-- Source: .claude/commands/erk/pr-preview-address.md -->

`pr-preview-address.md` uses direct skill invocation (`/pr-feedback-classifier`) because it only displays results without modifying any files. Context contamination has no effect on read-only operations.

## Related Documentation

- [Context Fork Feature](../claude-code/context-fork-feature.md) — Feature documentation and usage examples
