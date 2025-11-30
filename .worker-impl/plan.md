# Plan: Make `erk plan` Work as Verb and Noun

## Objective

Transform `erk plan` to serve dual purposes following the `git branch` pattern:

- **Verb** (no args): `erk plan` → launches remote planning via Codespace with auto-execute Claude
- **Noun** (with subcommands): `erk plan list`, `erk plan get <id>` → existing plan management

## Key Design Decisions

1. **Remote by default**: `erk plan` creates/reuses Codespace and auto-executes `/erk:craft-plan`
2. **Local option**: `erk plan --local` runs planning in current directory
3. **Auto-execute Claude**: SSH with command execution, not interactive SSH + manual invocation
4. **Replace `erk codespace plan`**: Move functionality to `erk plan`, remove from codespace group
5. **Keep `erk codespace init`**: Infrastructure setup remains under codespace group

## Implementation Steps

### Step 1: Extract Codespace Logic to Service Module

**Create `src/erk/core/codespace.py`**

Extract reusable functions from `plan_cmd.py`:

- `get_repo_name()` - Get repo in 'owner/repo' format via `gh repo view`
- `get_current_branch()` - Get branch via `git rev-parse`
- `find_existing_codespace(repo, branch)` - Find available Codespace
- `create_codespace(repo, branch)` - Create new Codespace with devcontainer
- `wait_for_codespace(codespace_name, timeout)` - Poll until available
- `get_or_create_codespace(repo, branch)` - Convenience wrapper

This enables code reuse without duplication.

### Step 2: Modify Plan Group with `invoke_without_command`

**Modify `src/erk/cli/commands/plan/__init__.py`**

Use Click's `invoke_without_command=True` pattern:

```python
@click.group("plan", invoke_without_command=True)
@click.option("--local", is_flag=True, help="Plan in current directory instead of remote Codespace")
@click.argument("description", required=False, default="")
@click.pass_context
def plan_group(ctx: click.Context, local: bool, description: str) -> None:
    """Manage implementation plans.

    When called without a subcommand, launches planning mode.
    """
    if ctx.invoked_subcommand is None:
        if local:
            _run_local_planning(description)
        else:
            _run_remote_planning(description)
```

### Step 3: Implement Remote Planning Function

**Add to `src/erk/cli/commands/plan/__init__.py`** (or separate module):

```python
def _run_remote_planning(description: str) -> None:
    """Create/reuse Codespace and auto-execute Claude with /erk:craft-plan."""
    from erk.core.codespace import get_or_create_codespace, get_repo_name, get_current_branch

    repo = get_repo_name()
    branch = get_current_branch()
    codespace_name = get_or_create_codespace(repo, branch)

    # Build slash command
    slash_cmd = "/erk:craft-plan"
    if description:
        slash_cmd = f"/erk:craft-plan {description}"

    # Auto-execute Claude via SSH with command
    ssh_cmd = [
        "gh", "codespace", "ssh",
        "-c", codespace_name,
        "--",  # Command follows
        "claude", "--permission-mode", "acceptEdits", slash_cmd
    ]

    user_output("Connecting to Codespace and starting planning...")
    os.execvp("gh", ssh_cmd)
```

### Step 4: Implement Local Planning Function

```python
def _run_local_planning(description: str) -> None:
    """Run Claude with /erk:craft-plan in current directory."""
    import shutil

    if shutil.which("claude") is None:
        user_output(click.style("Error: ", fg="red") + "Claude CLI not found.")
        raise SystemExit(1)

    slash_cmd = "/erk:craft-plan"
    if description:
        slash_cmd = f"/erk:craft-plan {description}"

    cmd = ["claude", "--permission-mode", "acceptEdits", slash_cmd]
    os.execvp("claude", cmd)
```

### Step 5: Remove `plan` from Codespace Group

**Modify `src/erk/cli/commands/codespace/__init__.py`**

```python
# Remove plan_codespace import and registration
codespace_group.add_command(init_codespace, name="init")
# Delete: codespace_group.add_command(plan_codespace, name="plan")
```

### Step 6: Update `init_cmd.py` Next Steps

**Modify `src/erk/cli/commands/codespace/init_cmd.py`** line ~63:

```python
# Change from:
user_output("  4. Create a Codespace: erk codespace plan <description>")

# To:
user_output("  4. Start remote planning: erk plan")
```

### Step 7: Clean Up `plan_cmd.py`

Either:

- **Delete** `src/erk/cli/commands/codespace/plan_cmd.py` entirely (functions moved to `codespace.py` service)
- **Or** keep as internal module if useful for reference

## Expected CLI Behavior

```bash
# Verb usage (planning mode)
erk plan                           # Remote: Codespace + auto-execute Claude
erk plan "add user auth"           # Remote with description
erk plan --local                   # Local: run Claude in current directory
erk plan --local "add user auth"   # Local with description

# Noun usage (plan management)
erk plan list                      # List all plans
erk plan list --state open         # List open plans
erk plan get 42                    # Get specific plan
erk plan create --file plan.md     # Create plan from file
erk plan check plan.md             # Validate plan format
erk plan close 42                  # Close a plan
erk plan log 42                    # Show plan event log
```

## Files to Modify

| File                                         | Change                                                    |
| -------------------------------------------- | --------------------------------------------------------- |
| `src/erk/core/codespace.py`                  | **NEW** - Extracted codespace service functions           |
| `src/erk/cli/commands/plan/__init__.py`      | Add `invoke_without_command`, options, planning functions |
| `src/erk/cli/commands/codespace/__init__.py` | Remove `plan_codespace` registration                      |
| `src/erk/cli/commands/codespace/plan_cmd.py` | Delete or deprecate                                       |
| `src/erk/cli/commands/codespace/init_cmd.py` | Update next steps message                                 |

## Testing

1. `erk plan` - triggers remote planning flow
2. `erk plan --local` - triggers local planning flow
3. `erk plan "description"` - passes description correctly
4. `erk plan list` - existing subcommand still works
5. `erk plan get 42` - existing subcommand still works
6. `erk plan --help` - shows correct help with options and subcommands
7. `erk codespace plan` - no longer exists (or shows deprecation warning)
