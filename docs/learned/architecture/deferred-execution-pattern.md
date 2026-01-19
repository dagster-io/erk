---
title: Deferred Execution Pattern
read_when:
  - "implementing operations that delete current worktree"
  - "implementing shell-level cd operations"
  - "implementing atomic multi-step operations"
  - "using --execute flags with state parameters"
---

# Deferred Execution Pattern

## Problem

Some CLI operations cannot complete within a single Python process:

1. **Worktree deletion**: Deleting the current working directory while the process is running
2. **Shell navigation**: Python `os.chdir()` only affects the Python process, not the user's shell
3. **Atomic sequences**: Multi-step operations that should appear as one unit to the user

## Solution: Two-Phase Execution

Split the operation into two phases:

### Phase 1: Validation and Script Generation (Python)

1. Validate all preconditions (fetch data, check permissions, prompt user)
2. Generate a shell script with all validated parameters
3. Write script to `.erk/bin/{name}.sh`
4. Print `source` instructions for user

### Phase 2: Execution (Shell)

User sources the script, which:

1. Executes the actual operations with `--execute` flag
2. Navigates to new location if needed
3. Cleans up resources

## Implementation Pattern

### Hidden `--execute` Flag

```python
@click.command()
@click.option("--execute", is_flag=True, hidden=True)
@click.option("--exec-pr-number", type=int, hidden=True)
@click.option("--exec-target-worktree", type=str, hidden=True)
def land(
    ctx: ErkContext,
    execute: bool,
    exec_pr_number: int | None,
    exec_target_worktree: str | None,
) -> None:
    if execute:
        # Phase 2: Execute with pre-validated state
        _execute_land(ctx, exec_pr_number, exec_target_worktree)
    else:
        # Phase 1: Validate and generate script
        _prepare_land(ctx)
```

### State Parameters

Use `--exec-*` prefixed parameters to pass validated state:

- `--exec-pr-number`: Pre-fetched PR number
- `--exec-target-worktree`: Pre-validated navigation target
- `--exec-force`: Signal that prompts were already confirmed

### Script Generation

```python
def _prepare_land(ctx: ErkContext) -> None:
    # 1. All validation and prompts happen here
    pr = fetch_pr(...)
    target = resolve_target_worktree(...)

    if has_uncommitted_changes():
        if not confirm("Proceed anyway?"):
            return

    # 2. Generate script with validated state
    script = render_land_script(
        pr_number=pr.number,
        target_worktree=target.path,
    )

    # 3. Write to worktree-scoped location
    script_path = ctx.script_writer.write_worktree_script(
        ctx.cwd, "land", script
    )

    # 4. Show source instructions
    print_temp_script_instructions(script_path)
```

### Generated Script Structure

```bash
#!/bin/bash
set -e

# Execute with pre-validated parameters
erk pr land \
    --execute \
    --exec-pr-number 123 \
    --exec-target-worktree /path/to/other/worktree

# Navigate (only works because this is sourced, not executed)
cd /path/to/other/worktree
source .erk/activate.sh
```

## Key Insights

### All Prompts in Validation Phase

The execution phase must use `force=True` or equivalent to skip prompts. By the time execution runs, the user has already confirmed by sourcing the script.

### Worktree Scripts vs Temp Scripts

- **Temp scripts** (`/tmp/erk_*.sh`): One-time navigation, deleted after use
- **Worktree scripts** (`.erk/bin/*.sh`): Deferred operations that may be inspected or re-run

### Error Handling

Validation phase should catch all predictable errors. Execution phase failures are rare but may leave partial state - this is acceptable because the user is present and can recover.

## When to Use

Use deferred execution when:

- Operation deletes or moves the current working directory
- User's shell must navigate to a new location
- Multiple operations must appear atomic to the user
- Operation requires resources that will be unavailable during execution

## Example: Land Command

The `erk pr land` command demonstrates this pattern:

1. **Validation**: Fetch PR, check merge status, resolve navigation target, prompt for confirmation
2. **Script**: Write `.erk/bin/land.sh` with `--execute` and all `--exec-*` params
3. **Execution**: Merge PR, delete worktree, navigate to target

## Related

- [Activation Scripts](../cli/activation-scripts.md) - Script writing utilities
- [Erk Architecture Patterns](erk-architecture.md) - General architecture patterns
