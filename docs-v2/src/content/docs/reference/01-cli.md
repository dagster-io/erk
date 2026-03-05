---
title: CLI reference
description: Complete reference for erk CLI commands
sidebar:
  order: 1
---

Erk provides a CLI for managing plans, worktrees, and PR workflows.

## Top-level commands

### `erk pr list`

List open plans and their status.

```bash
erk pr list
```

### `erk pr create`

Create a new plan from a markdown file.

```bash
erk pr create --file plan.md
```

### `erk implement`

Implement a plan in an isolated worktree.

```bash
erk implement 1234
```

### `erk pr dispatch`

Dispatch a plan for remote autonomous implementation.

```bash
erk pr dispatch 1234
```

### `erk pr submit`

Push the current branch and create or update its PR.

```bash
erk pr submit
```

## Worktree commands

### `erk wt list`

List all managed worktrees.

```bash
erk wt list
```

### `erk wt create`

Create a new worktree for development.

```bash
erk wt create my-feature
```

## Stack commands

### `erk stack list`

Show the current stack of dependent branches.

```bash
erk stack list
```

## Exec commands

Erk's `exec` subcommand provides lower-level operations used by skills and automation:

```bash
erk exec setup-impl --issue 1234
erk exec impl-signal started
erk exec cleanup-impl-context
```

See `erk exec --help` for the full list of available subcommands.

---

:::note
This reference covers the most commonly used commands. Run `erk --help` or `erk <command> --help` for complete usage information.
:::
