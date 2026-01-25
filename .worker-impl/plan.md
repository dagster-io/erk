# Plan: Unify Local/Remote Command Pattern

## Goal

Establish a consistent pattern for CLI commands with local/remote variants:
- `erk pr <command>` = local execution (default)
- `erk pr <command> remote` = remote execution (subcommand)

## Pattern Reference

Based on `erk init` in `src/erk/cli/commands/init/__init__.py`:
```python
@click.group("init", cls=ErkCommandGroup, invoke_without_command=True)
@click.option(...)
@click.pass_context
def init_group(ctx: click.Context, *, options...) -> None:
    if ctx.invoked_subcommand is None:
        # Default behavior when no subcommand given
        run_init(ctx.obj, ...)
```

## Changes

### 1. Convert `fix-conflicts` to Group

**File:** `src/erk/cli/commands/pr/fix_conflicts_cmd.py`

- Convert from `@click.command` to `@click.group(invoke_without_command=True)`
- Keep existing local logic in a helper function called when no subcommand
- Add `remote` as a subcommand with the logic from `fix_conflicts_remote_cmd.py`

### 2. Create `address` Group

**File:** `src/erk/cli/commands/pr/address_cmd.py` (new)

Create new group with:
- **Local variant** (default): Invoke `/erk:pr-address` Claude command using `stream_command_with_feedback()` pattern
- **Remote variant** (`remote` subcommand): Move logic from `address_remote_cmd.py`

Local address implementation uses:
- `ctx.claude_executor.is_claude_available()` to check Claude
- `stream_command_with_feedback()` from `erk.cli.output` to invoke `/erk:pr-address`

### 3. Update PR Group Registration

**File:** `src/erk/cli/commands/pr/__init__.py`

```python
# Before
from erk.cli.commands.pr.address_remote_cmd import pr_address_remote
from erk.cli.commands.pr.fix_conflicts_cmd import pr_fix_conflicts
from erk.cli.commands.pr.fix_conflicts_remote_cmd import pr_fix_conflicts_remote

pr_group.add_command(pr_address_remote, name="address-remote")
pr_group.add_command(pr_fix_conflicts, name="fix-conflicts")
pr_group.add_command(pr_fix_conflicts_remote, name="fix-conflicts-remote")

# After
from erk.cli.commands.pr.address_cmd import address_group
from erk.cli.commands.pr.fix_conflicts_cmd import fix_conflicts_group

pr_group.add_command(address_group, name="address")
pr_group.add_command(fix_conflicts_group, name="fix-conflicts")
```

### 4. Update TUI Command Registry

**File:** `src/erk/tui/commands/registry.py`

```python
# Before
def _display_fix_conflicts_remote(ctx: CommandContext) -> str:
    return f"erk pr fix-conflicts-remote {ctx.row.pr_number}"

def _display_address_remote(ctx: CommandContext) -> str:
    return f"erk pr address-remote {ctx.row.pr_number}"

# After
def _display_fix_conflicts_remote(ctx: CommandContext) -> str:
    return f"erk pr fix-conflicts remote {ctx.row.pr_number}"

def _display_address_remote(ctx: CommandContext) -> str:
    return f"erk pr address remote {ctx.row.pr_number}"
```

### 5. Update Claude Command

**File:** `.claude/commands/erk/pr-address-remote.md`

Update the CLI invocation from `erk pr address-remote` to `erk pr address remote`

### 6. Update Tests

**Files to update:**
- `tests/commands/pr/test_fix_conflicts.py` - Keep as is (tests local variant)
- `tests/commands/pr/test_fix_conflicts_remote.py` - Update command invocations from `["fix-conflicts-remote"]` to `["fix-conflicts", "remote"]`
- `tests/commands/pr/test_address_remote_cmd.py` - Update command invocations from `["address-remote", "123"]` to `["address", "remote", "123"]`

**New test file:**
- `tests/commands/pr/test_address.py` - Tests for local `erk pr address` (Claude invocation)

## Files Summary

**Modify:**
1. `src/erk/cli/commands/pr/fix_conflicts_cmd.py` - Convert to group, add remote subcommand
2. `src/erk/cli/commands/pr/__init__.py` - Update imports and registrations
3. `src/erk/tui/commands/registry.py` - Update display strings
4. `.claude/commands/erk/pr-address-remote.md` - Update CLI invocation
5. `tests/commands/pr/test_fix_conflicts_remote.py` - Update command args
6. `tests/commands/pr/test_address_remote_cmd.py` - Update command args

**Create:**
1. `src/erk/cli/commands/pr/address_cmd.py` - New group with local + remote
2. `tests/commands/pr/test_address.py` - Tests for local address

**Delete:**
1. `src/erk/cli/commands/pr/fix_conflicts_remote_cmd.py`
2. `src/erk/cli/commands/pr/address_remote_cmd.py`

## Verification

1. CLI help output:
   ```bash
   erk pr --help  # Should show 'address' and 'fix-conflicts' (no '-remote' variants)
   erk pr address --help  # Should show 'remote' subcommand
   erk pr fix-conflicts --help  # Should show 'remote' subcommand
   ```

2. Test commands:
   ```bash
   # Local variants
   erk pr fix-conflicts --dangerous  # Requires conflicts
   erk pr address --dangerous        # Invokes Claude

   # Remote variants
   erk pr fix-conflicts remote --help
   erk pr address remote 123 --help
   ```

3. Run tests:
   ```bash
   uv run pytest tests/commands/pr/test_fix_conflicts.py
   uv run pytest tests/commands/pr/test_fix_conflicts_remote.py
   uv run pytest tests/commands/pr/test_address_remote_cmd.py
   uv run pytest tests/commands/pr/test_address.py
   ```