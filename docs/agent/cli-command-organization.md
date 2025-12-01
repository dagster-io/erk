# CLI Command Organization

## Design Philosophy: Plan-Oriented Interface

Erk's CLI is organized around the principle that **plans are the dominant noun** in the user's workflow. This design decision prioritizes ergonomics for the most common operations while maintaining clarity through consistent grouping patterns.

### Core Principle: Plan as First-Class Citizen

Plans represent implementation work to be done. Since users interact with plans more frequently than they manipulate worktrees or stacks directly, plan-related commands are placed at the top level for minimal keystrokes and maximum discoverability.

**Top-level plan commands:**

```bash
erk create        # Create a new plan issue
erk get           # View a plan
erk dash          # Display plan dashboard
erk close         # Close a plan
erk implement     # Implement a plan
erk submit        # Submit a plan for remote execution
erk log           # View plan execution logs
```

**Why top-level?**

- High-frequency operations: Users create, view, and implement plans constantly
- Natural mental model: "I want to work on a plan" → `erk implement 42`
- Minimal friction: 2 words instead of 3 (`erk plan get` → `erk get`)

## Command Categories

### Top-Level Plan Operations

Plan commands appear at the top level without a noun prefix:

| Command     | Description                     | Frequency |
| ----------- | ------------------------------- | --------- |
| `dash`      | Display plan dashboard          | Very High |
| `get`       | View plan details               | High      |
| `create`    | Create new plan issue           | High      |
| `close`     | Close a plan                    | Medium    |
| `implement` | Start implementing a plan       | Very High |
| `submit`    | Queue plan for remote execution | High      |
| `log`       | View plan execution history     | Medium    |

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

- Lower frequency: Most worktrees are created automatically via `erk implement`
- Infrastructure concern: Users think "I want to implement this plan" not "I want a worktree"
- Namespace clarity: Avoids collision with plan commands

#### Stack Operations (`erk stack <verb>`)

Graphite stack management for dependent branches:

```bash
erk stack submit           # Submit entire stack
erk stack sync             # Sync stack with remote
erk stack restack          # Rebase stack on trunk
```

**Why grouped?**

- Graphite-specific: Only relevant when using stacked workflows
- Advanced usage: Not part of basic plan workflow
- Clear domain: "Stack" immediately indicates Graphite operations

### Navigation Commands (Top-Level)

Branch/worktree navigation commands are top-level because they're fundamental movement operations:

```bash
erk checkout <branch>      # Switch to worktree for branch (alias: co)
erk up                     # Navigate to parent branch
erk down                   # Navigate to child branch
```

**Why top-level?**

- Very high frequency: Navigation is constant during development
- Movement primitive: Like `cd` in shell, should be minimal keystrokes
- Natural workflow: "Switch to that branch" → `erk co feature-branch`

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
        │ (restack, sync, submit stack)        │
        └─────────┬───────────────────────────┘
                  │
            ┌─────▼─────┐
            │    YES    │
            └─────┬─────┘
                  │
            ┌─────▼────────────────────────────┐
            │ Group under `erk stack <verb>`    │
            │ Examples: stack submit, stack sync│
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

### ✅ Plan Operations at Top Level

```bash
# GOOD: Direct, minimal keystrokes
erk create --file plan.md
erk implement 42
erk get 42

# BAD: Unnecessary grouping adds friction
erk plan create --file plan.md
erk plan implement 42
erk plan get 42
```

**Why?** Plans are the primary workflow object. Extra nesting adds cognitive load.

### ✅ Infrastructure Grouped Under Noun

```bash
# GOOD: Clear namespace, infrastructure is grouped
erk wt create my-feature
erk wt delete old-feature
erk stack restack

# BAD: Conflicts with plan operations, unclear ownership
erk create my-feature     # Is this a plan or worktree?
erk delete old-feature    # What am I deleting?
erk restack               # Restack what?
```

**Why?** Grouping clarifies the target domain and prevents naming collisions.

### ✅ Navigation as Movement Primitives

```bash
# GOOD: Minimal, like shell commands (cd, ls)
erk checkout feature-branch
erk co feature-branch      # Alias
erk up
erk down

# BAD: Over-grouped, breaks natural flow
erk nav checkout feature-branch
erk nav up
erk nav down
```

**Why?** Navigation is a fundamental movement operation, should be as lightweight as possible.

## Anti-Patterns

### ❌ Grouping High-Frequency Operations

```bash
# BAD: Adds friction to common operations
erk plan create
erk plan implement
erk plan get

# GOOD: Direct access for frequent tasks
erk create
erk implement
erk get
```

### ❌ Top-Level Infrastructure Commands

```bash
# BAD: Name collision, unclear scope
erk create <name>         # Create what? Plan or worktree?
erk delete <name>         # Delete what?

# GOOD: Explicit namespace
erk create --file plan.md  # Clearly a plan
erk wt create <name>       # Clearly a worktree
erk wt delete <name>       # Clearly a worktree
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
erk create --file implementation-plan.md

# View plans
erk dash                  # Display plan dashboard
erk get 42                # View specific plan

# Work on a plan
erk implement 42          # Create worktree and start work

# Submit for execution
erk submit 42             # Queue for remote execution

# Track progress
erk log 42                # View execution history
erk status                # Current worktree status

# Finish
erk close 42              # Close completed plan
```

### Worktree Management

```bash
# Create worktrees (rare - usually via implement)
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
erk checkout feature-branch
erk co fb                 # Alias with fuzzy match

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
| Navigation        | `src/erk/cli/commands/{checkout,up,down}.py` |
| Setup             | `src/erk/cli/commands/{init,config}.py`      |

## Related Documentation

- [Kit CLI Commands](kit-cli-commands.md) - Kit-based command patterns
- [CLI Output Styling](cli-output-styling.md) - Output formatting guidelines
- [CLI Script Mode](cli-script-mode.md) - Shell integration patterns
- [Command Agent Delegation](command-agent-delegation.md) - When to delegate to agents
