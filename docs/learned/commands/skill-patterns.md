---
title: Skill and Command Patterns
read_when:
  - "creating slash commands that involve user decisions"
  - "using AskUserQuestion in commands or skills"
  - "naming prompt executor functions"
tripwires:
  - action: "hardcoding a choice in a command where user should decide"
    warning: "use AskUserQuestion to present options. Commands should empower user decisions, not make them."
---

# Skill and Command Patterns

Patterns for writing effective slash commands and skills.

## AskUserQuestion for User-Facing Decisions

When a command reaches a point where the user should choose between valid options, use `AskUserQuestion` to present the choices rather than picking one automatically.

### Example: pr-rebase.md

After a rebase, the branch has diverged from origin. The pr-rebase command uses `AskUserQuestion` to ask how to proceed:

- **Push with Graphite**: `gt submit --no-interactive`
- **Push with git**: `git push --force-with-lease`
- **Do nothing**: skip pushing (user handles manually)

Reference: `.claude/commands/erk/pr-rebase.md` Step 8

### When to Use

- Multiple valid next actions exist after a command step
- The choice has consequences the user should control (e.g., force push)
- The command is interactive (not a batch/automation command)

## Naming Convention: prompt_executor

Functions that orchestrate LLM-driven prompt execution should be named `prompt_executor`, not `llm_caller`. This reflects the function's role as an executor of structured prompts, not a generic LLM wrapper.
