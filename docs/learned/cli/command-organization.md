---
title: CLI Command Organization
last_audited: "2026-02-16 04:53 PT"
audit_result: clean
read_when:
  - "organizing CLI commands"
  - "understanding command structure"
  - "designing command hierarchies"
---

# CLI Command Organization

## Design Philosophy: Plan-Oriented Interface

Erk's CLI is organized around the principle that **plans are the dominant noun** in the user's workflow. This design decision prioritizes ergonomics for the most common operations while maintaining clarity through consistent grouping patterns.

### Core Principle: Plan as First-Class Citizen

Plans represent implementation work to be done. Since users interact with plans more frequently than they manipulate worktrees or stacks directly, plan-related commands are placed at the top level for minimal keystrokes and maximum discoverability.

**Top-level plan commands:**

```bash
erk dash          # Display plan dashboard
erk implement     # Implement a plan in current directory
erk prepare       # Create a worktree from a plan issue

# Most plan management operations are under `erk plan`:
erk plan create   # Create a new plan issue
erk plan view     # View a plan
erk plan close    # Close a plan
erk plan submit   # Submit a plan for remote execution
erk plan log      # View plan execution logs
```

**Why top-level?**

- Highest-frequency entry points: `implement`, `prepare`, and `dash` are the most common workflow starters
- Natural mental model: "I want to work on a plan" → `erk implement 42`
- Plan management via `erk plan <subcommand>`: `create`, `view`, `close`, `submit`, `log`, etc.

## Command Categories

### Top-Level Plan Operations

Only the highest-frequency workflow entry points are at the top level:

| Command     | Description                              | Frequency |
| ----------- | ---------------------------------------- | --------- |
| `dash`      | Display plan dashboard                   | Very High |
| `implement` | Implement a plan in current directory    | Very High |
| `prepare`   | Create a worktree from a plan issue      | High      |

### `erk plan` Subcommands

All other plan management operations are under the `erk plan` group (table reflects `erk plan --help` output):

| Subcommand   | Description                              |
| ------------ | ---------------------------------------- |
| `create`     | Create a new plan issue                  |
| `view`       | View a plan                              |
| `list`       | List open plans                          |
| `close`      | Close a plan                             |
| `submit`     | Submit a plan for remote execution       |
| `log`        | View plan execution logs                 |
| `replan`     | Replan an existing plan issue            |
| `checkout`   | Check out a plan's branch (alias: `co`)  |
| `check`      | Check plan status                        |

### Grouped Commands

Infrastructure and supporting operations are grouped under noun prefixes for clarity:

#### Worktree Operations (`erk wt <verb>`)

Worktree manipulation is a supporting operation, not the primary workflow:

```bash
erk wt create <name>        # Create a new worktree
erk wt delete <name>        # Delete a worktree
erk wt list                 # List worktrees
erk wt prune                # Clean up stale worktrees
```

**Why grouped?**

- Lower frequency: Worktrees are created implicitly during plan implementation, not managed directly
- Infrastructure concern: Users think "I want to implement this plan" not "I want a worktree"
- Namespace clarity: Avoids collision with plan commands

#### Stack Operations (`erk stack <verb>`)

Graphite stack management for dependent branches:

```bash
erk stack consolidate      # Consolidate stack changes
erk stack list             # List stack items
erk stack move             # Move item in stack
erk stack split            # Split stack at a point
```

**Why grouped?**

- Graphite-specific: Only relevant when using stacked workflows
- Advanced usage: Not part of basic plan workflow
- Clear domain: "Stack" immediately indicates Graphite operations

### Navigation Commands (Top-Level)

Branch/worktree navigation commands are top-level because they're fundamental movement operations:

```bash
erk br co <branch>         # Switch to worktree for branch (alias for erk branch checkout)
erk up                     # Navigate to parent branch
erk down                   # Navigate to child branch
```

**Why top-level?**

- Very high frequency: Navigation is constant during development
- Movement primitive: Like `cd` in shell, should be minimal keystrokes
- Natural workflow: "Switch to that branch" → `erk br co feature-branch`

### Setup and Configuration

Initial setup commands (used once or rarely):

```bash
erk init                   # Initialize erk in repository
erk config                 # Configure erk settings
```

## Decision Framework

When adding a new command, use this flowchart to determine placement:

```
┌─────────────────────────────────────────┐
│ Is this a plan-related operation?       │
│ (create, view, modify, execute plans)   │
└─────────┬───────────────────────────────┘
          │
    ┌─────▼─────┐
    │    YES    │
    └─────┬─────┘
          │
    ┌─────▼──────────────────────────────────────┐
    │ Place at TOP LEVEL                          │
    │ Examples: implement, prepare, dash          │
    └─────────────────────────────────────────────┘

          │ NO
    ┌─────▼─────────────────────────────────┐
    │ Is this worktree infrastructure?       │
    │ (create, delete, manage worktrees)     │
    └─────────┬───────────────────────────────┘
              │
        ┌─────▼─────┐
        │    YES    │
        └─────┬─────┘
              │
        ┌─────▼─────────────────────────┐
        │ Group under `erk wt <verb>`    │
        │ Examples: wt create, wt delete │
        └────────────────────────────────┘

              │ NO
        ┌─────▼───────────────────────────────┐
        │ Is this Graphite stack management?   │
        │ (consolidate, move, split stack)     │
        └─────────┬───────────────────────────┘
                  │
            ┌─────▼─────┐
            │    YES    │
            └─────┬─────┘
                  │
            ┌─────▼────────────────────────────┐
            │ Group under `erk stack <verb>`    │
            │ Examples: stack consolidate, stack list│
            └───────────────────────────────────┘

                  │ NO
            ┌─────▼─────────────────────────────┐
            │ Is this navigation/movement?       │
            │ (switch branches, move up/down)    │
            └─────────┬─────────────────────────┘
                      │
                ┌─────▼─────┐
                │    YES    │
                └─────┬─────┘
                      │
                ┌─────▼────────────────────────┐
                │ Place at TOP LEVEL            │
                │ Examples: checkout, up, down  │
                └───────────────────────────────┘

                      │ NO
                ┌─────▼──────────────────────────┐
                │ Place at TOP LEVEL              │
                │ (default for misc operations)   │
                │ Examples: init, config, status  │
                └─────────────────────────────────┘
```

## Good Patterns

### ✅ Plan Operations: Top-Level vs `erk plan` Subcommands

```bash
# GOOD: Top-level for highest-frequency entry points
erk implement 42
erk prepare 42
erk dash

# GOOD: erk plan subcommands for plan management operations
erk plan create --file plan.md
erk plan view 42
erk plan close 42
erk plan submit 42
```

**Why?** Only `implement`, `prepare`, and `dash` are top-level — they are the most common workflow entry points. All other plan operations (create, view, close, submit, log, etc.) live under `erk plan <subcommand>`.

### ✅ Infrastructure Grouped Under Noun

```bash
# GOOD: Clear namespace, infrastructure is grouped
erk wt create my-feature
erk wt delete old-feature
erk stack consolidate

# BAD: Conflicts with plan operations, unclear ownership
erk create my-feature     # Is this a plan or worktree?
erk delete old-feature    # What am I deleting?
erk consolidate           # Consolidate what?
```

**Why?** Grouping clarifies the target domain and prevents naming collisions.

### ✅ Navigation as Movement Primitives

```bash
# GOOD: Minimal, like shell commands (cd, ls)
erk br co feature-branch
erk up
erk down

# BAD: Over-grouped, breaks natural flow
erk nav checkout feature-branch
erk nav up
erk nav down
```

**Why?** Navigation is a fundamental movement operation, should be as lightweight as possible.

## Anti-Patterns

### ❌ Top-Level Infrastructure Commands

```bash
# BAD: Name collision, unclear scope
erk create <name>         # Create what? Plan or worktree?
erk delete <name>         # Delete what?

# GOOD: Explicit namespace
erk plan create --file plan.md  # Clearly a plan
erk wt create <name>            # Clearly a worktree
erk wt delete <name>            # Clearly a worktree
```

### ❌ Inconsistent Grouping

```bash
# BAD: Some worktree ops grouped, others not
erk wt create
erk wt delete
erk list-worktrees        # Should be: erk wt list

# GOOD: Consistent grouping
erk wt create
erk wt delete
erk wt list
```

## Examples by Category

### Plan Lifecycle

```bash
# Create a plan
erk plan create --file implementation-plan.md

# View plans
erk dash                  # Display plan dashboard
erk plan view 42          # View specific plan

# Work on a plan
erk implement 42          # Set up .impl/ and implement in current directory

# Submit for execution
erk plan submit 42        # Queue for remote execution

# Track progress
erk plan log 42           # View execution history

# Finish
erk plan close 42         # Close completed plan
```

### Worktree Management

```bash
# Create worktrees
erk wt create my-feature

# List and inspect
erk wt list               # List worktrees

# Clean up
erk wt delete my-feature
erk wt prune              # Remove stale worktrees
```

### Navigation

```bash
# Switch between branches
erk br co feature-branch

# Navigate stack
erk up                    # Move to parent branch
erk down                  # Move to child branch
```

## Implementation Reference

### Adding a New Command

**Step 1: Determine placement** using the decision framework above

**Step 2: Create command file**

- Plan command: `src/erk/cli/commands/plan/<name>_cmd.py`
- Worktree command: `src/erk/cli/commands/wt/<name>_cmd.py`
- Stack command: `src/erk/cli/commands/stack/<name>_cmd.py`
- Top-level: `src/erk/cli/commands/<name>.py`

**Step 3: Register in `src/erk/cli/cli.py`**

For plan commands (top-level):

```python
from erk.cli.commands.plan.create_cmd import create_plan

cli.add_command(create_plan, name="create")  # Plan command
```

For grouped commands:

```python
from erk.cli.commands.wt.create_cmd import create_wt

wt_group.add_command(create_wt)  # Grouped under wt
```

**Step 4: Add tests**

- Plan commands: `tests/commands/plan/test_<name>.py`
- Worktree commands: `tests/commands/wt/test_<name>.py`
- Stack commands: `tests/commands/stack/test_<name>.py`

### Code Locations

| Component         | Location                                     |
| ----------------- | -------------------------------------------- |
| CLI entry point   | `src/erk/cli/cli.py`                         |
| Plan commands     | `src/erk/cli/commands/plan/`                 |
| Worktree commands | `src/erk/cli/commands/wt/`                   |
| Stack commands    | `src/erk/cli/commands/stack/`                |
| Navigation        | `src/erk/cli/commands/branch/checkout_cmd.py`, `up.py`, `down.py` |
| Setup             | `src/erk/cli/commands/init/` (directory), `src/erk/cli/commands/config.py` |

## Related Documentation

- [CLI Output Styling](output-styling.md) - Output formatting guidelines
