---
title: CLI Command Organization
read_when:
  - "organizing CLI commands"
  - "understanding command structure"
  - "designing command hierarchies"
last_audited: "2026-02-07 14:05 PT"
audit_result: edited
---

# CLI Command Organization

## Design Philosophy: Plan-Oriented Interface

Erk's CLI is organized around the principle that **plans are the dominant noun** in the user's workflow. This design decision prioritizes ergonomics for the most common operations while maintaining clarity through consistent grouping patterns.

### Core Principle: Plan as First-Class Citizen

Plans represent implementation work to be done. Since users interact with plans more frequently than they manipulate worktrees or stacks directly, plan-related commands are placed at the top level for minimal keystrokes and maximum discoverability.

**Top-level commands (truly top-level in `cli.py`):**

```bash
erk implement     # Implement a plan (alias: erk impl)
erk dash          # Display plan dashboard
erk up            # Navigate to parent branch
erk down          # Navigate to child branch
```

**Plan group commands (`erk plan <verb>`):**

```bash
erk plan create   # Create a new plan issue
erk plan view     # View a plan
erk plan close    # Close a plan
erk plan submit   # Submit a plan for remote execution
erk plan log      # View plan execution history
erk plan list     # List plans
```

**Why `implement` is top-level but others are grouped:**

- `implement` is the highest-frequency plan operation
- Other plan operations share a clear "plan" noun → natural grouping
- See `src/erk/cli/cli.py` for the full registration

## Command Categories

### Top-Level Commands

High-frequency commands registered directly on the CLI root:

| Command     | Description               | Frequency |
| ----------- | ------------------------- | --------- |
| `implement` | Start implementing a plan | Very High |
| `dash`      | Display plan dashboard    | Very High |
| `up`        | Navigate to parent branch | Very High |
| `down`      | Navigate to child branch  | Very High |

### Plan Group (`erk plan <verb>`)

Plan management commands grouped under the `plan` noun:

| Command       | Description                     | Frequency |
| ------------- | ------------------------------- | --------- |
| `plan create` | Create new plan issue           | High      |
| `plan view`   | View plan details               | High      |
| `plan close`  | Close a plan                    | Medium    |
| `plan submit` | Queue plan for remote execution | High      |
| `plan log`    | View plan execution history     | Medium    |
| `plan list`   | List plans                      | Medium    |

### Grouped Commands

Infrastructure and supporting operations are grouped under noun prefixes for clarity:

#### Worktree Operations (`erk wt <verb>`)

Worktree manipulation is a supporting operation, not the primary workflow:

```bash
erk wt create <name>        # Create a new worktree
erk wt delete <name>        # Delete a worktree
erk wt list                 # List worktrees
erk wt rename               # Rename a worktree
erk wt status               # Show worktree status
```

**Why grouped?**

- Lower frequency: Most worktrees are created automatically via `erk implement`
- Infrastructure concern: Users think "I want to implement this plan" not "I want a worktree"
- Namespace clarity: Avoids collision with plan commands

#### Stack Operations (`erk stack <verb>`)

Graphite stack management for dependent branches:

```bash
erk stack consolidate      # Consolidate stack branches
erk stack move             # Move branch within stack
erk stack split            # Split a branch in the stack
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
    │ Examples: create, get, implement, close     │
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
        │ (consolidate, move, split)           │
        └─────────┬───────────────────────────┘
                  │
            ┌─────▼─────┐
            │    YES    │
            └─────┬─────┘
                  │
            ┌─────▼────────────────────────────┐
            │ Group under `erk stack <verb>`    │
            │ Examples: stack consolidate, move │
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

### ✅ Highest-Frequency Operations at Top Level

```bash
# GOOD: implement is top-level for minimal keystrokes
erk implement 42
erk dash

# Other plan operations use the plan group
erk plan create --file plan.md
erk plan view 42
```

**Why?** `implement` is the most frequent operation. Other plan commands benefit from the `plan` namespace for clarity and discoverability.

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

### ❌ Grouping the Highest-Frequency Operation

```bash
# BAD: Adds friction to the most common operation
erk plan implement 42

# GOOD: Top-level for implement since it's the most frequent
erk implement 42
```

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
erk implement 42          # Create worktree and start work

# Submit for execution
erk plan submit 42        # Queue for remote execution

# Track progress
erk plan log 42           # View execution history

# Finish
erk plan close 42         # Close completed plan
```

### Worktree Management

```bash
# Create worktrees (rare - usually via implement)
erk wt create my-feature

# List and inspect
erk wt list               # List worktrees

# Clean up
erk wt delete my-feature
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

See `src/erk/cli/cli.py` for top-level registration and `src/erk/cli/commands/plan/__init__.py` for plan group registration. Commands with aliases use `register_with_aliases()` from `erk.cli.alias`.

**Step 4: Add tests**

- Plan commands: `tests/commands/plan/test_<name>.py`
- Worktree commands: `tests/commands/wt/test_<name>.py`
- Stack commands: `tests/commands/stack/test_<name>.py`

### Code Locations

| Component         | Location                            |
| ----------------- | ----------------------------------- |
| CLI entry point   | `src/erk/cli/cli.py`                |
| Plan commands     | `src/erk/cli/commands/plan/`        |
| Worktree commands | `src/erk/cli/commands/wt/`          |
| Stack commands    | `src/erk/cli/commands/stack/`       |
| Navigation        | `src/erk/cli/commands/{up,down}.py` |
| Branch group      | `src/erk/cli/commands/branch/`      |
| Setup             | `src/erk/cli/commands/init/`        |
| Config            | `src/erk/cli/commands/config.py`    |

## Related Documentation

- [CLI Output Styling](output-styling.md) - Output formatting guidelines
- [Command Agent Delegation](../planning/agent-delegation.md) - When to delegate to agents
