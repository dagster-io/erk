---
title: Naming Conventions
read_when:
  - "naming functions or variables"
  - "creating CLI commands"
  - "naming Claude artifacts"
---

# Naming Conventions

This document defines naming conventions for the erk codebase.

## Code Naming

| Element             | Convention         | Example                          |
| ------------------- | ------------------ | -------------------------------- |
| Functions/variables | `snake_case`       | `create_worktree`, `branch_name` |
| Classes             | `PascalCase`       | `WorktreeManager`, `GitOps`      |
| Constants           | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| CLI commands        | `kebab-case`       | `erk create`, `erk wt list`      |

## Claude Artifacts

All files in `.claude/` (commands, skills, agents, hooks) MUST use `kebab-case`.

**Examples:**

- ✅ `/my-command` (correct)
- ❌ `/my_command` (wrong - uses underscore)

**Exception:** Python scripts within artifacts may use `snake_case` (they're code, not artifacts).

## Brand Names

Use proper capitalization for brand names:

- **GitHub** (not Github)
- **Graphite** (not graphite)

## Worktree Terminology

Use "root worktree" (not "main worktree") to refer to the primary git worktree created with `git init`. This ensures "main" unambiguously refers to the branch name, since trunk branches can be named either "main" or "master".

In code, use the `is_root` field to identify the root worktree.

## CLI Command Organization

Plan verbs are top-level (create, get, implement), worktree verbs are grouped under `erk wt`, stack verbs under `erk stack`. This follows the "plan is dominant noun" principle for ergonomic access to high-frequency operations.

See [cli-command-organization.md](cli-command-organization.md) for the complete decision framework.
