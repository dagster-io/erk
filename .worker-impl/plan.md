# Plan: Canonicalize Init Command Test Input Strings

## Problem

The `erk init` tests have 14+ hardcoded input strings like `"n\nn\nn\ny\nn\n"` that must be manually updated when prompts change. This is fragile and error-prone.

## Root Cause

The init command uses TWO different confirm mechanisms:
1. `click.confirm()` for gitignore prompts (line 153) - reads from stdin, NOT fakeable
2. `_console.confirm()` for permissions (lines 270, 279, 347, 410) - uses module-level global

The test infrastructure already supports `FakeConsole.confirm_responses=[True, False, ...]` via `env.build_context(confirm_responses=[...])`, but this only works for `_console.confirm()` calls.

## Solution

Unify all confirmations through the injected console, allowing tests to use structured `confirm_responses` lists instead of magic input strings.

## Implementation Steps

### Step 1: Modify gitignore prompt function to accept console

**File**: `src/erk/cli/commands/init/main.py`

Change `_add_gitignore_entry_with_prompt()` to accept a `console` parameter:

```python
def _add_gitignore_entry_with_prompt(
    content: str,
    entry: str,
    prompt_message: str,
    console: Console,  # Add this
) -> tuple[str, bool]:
    # ...
    if not console.confirm(prompt_message, default=True):  # Was: click.confirm()
        return (content, False)
```

### Step 2: Modify backup cleanup to accept console

**File**: `src/erk/cli/commands/init/main.py`

Change `offer_backup_cleanup()`:

```python
def offer_backup_cleanup(backup_path: Path, console: Console) -> None:
    if console.confirm("Delete backup?", default=True):  # Was: click.confirm()
        backup_path.unlink()
```

### Step 3: Update _run_gitignore_prompts to accept and pass console

**File**: `src/erk/cli/commands/init/main.py`

```python
def _run_gitignore_prompts(repo_root: Path, console: Console) -> None:
    # Pass console to each call
    gitignore_content, env_added = _add_gitignore_entry_with_prompt(
        gitignore_content, ".env", "Add .env to .gitignore?", console
    )
    # ... repeat for other entries
```

### Step 4: Update run_init() to pass ctx.console

**File**: `src/erk/cli/commands/init/main.py`

In `run_init()`:
- Change `_run_gitignore_prompts(repo_context.root)` to `_run_gitignore_prompts(repo_context.root, ctx.console)`
- Change `offer_backup_cleanup(pending_backup)` to `offer_backup_cleanup(pending_backup, ctx.console)`
- Change `_console.confirm(...)` calls to `ctx.console.confirm(...)`

### Step 5: Remove module-level _console

**File**: `src/erk/cli/commands/init/main.py`

Delete line 48: `_console = InteractiveConsole()`

(No longer needed - all confirms go through `ctx.console`)

### Step 6: Update tests to use confirm_responses

**Files**:
- `tests/commands/setup/init/test_gitignore.py`
- `tests/commands/setup/init/test_claude_permissions.py`
- `tests/commands/setup/init/test_global_config.py`

Replace `input="y\nn\nn\nn\nn\n"` with `confirm_responses=[True, False, False, False, False]`:

```python
# Before
result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\nn\nn\nn\nn\n")

# After
test_ctx = env.build_context(
    git=git_ops,
    erk_installation=erk_installation,
    global_config=global_config,
    confirm_responses=[True, False, False, False, False],
)
result = runner.invoke(cli, ["init"], obj=test_ctx)
```

### Step 7: Handle path prompt (erk_root)

The `click.prompt()` for erk_root path (line 474) is only used during first-time init when no global config exists. Keep using `input="..."` for this specific case only:

```python
# Only for tests that need to provide erk_root path
result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{erk_root}\n")
```

This is acceptable because:
- Path prompts are rare (only first init)
- Only 1-2 tests need this
- Adding `Console.prompt()` is out of scope

## Files Modified

| File | Changes |
|------|---------|
| `src/erk/cli/commands/init/main.py` | Add console param to 3 functions, pass ctx.console, remove _console global |
| `tests/commands/setup/init/test_gitignore.py` | Replace 5 input= with confirm_responses |
| `tests/commands/setup/init/test_claude_permissions.py` | Replace 5 input= with confirm_responses |
| `tests/commands/setup/init/test_global_config.py` | Keep input= for erk_root prompt, add confirm_responses for confirmations |

## Benefits

1. **Semantic clarity**: `confirm_responses=[True, False, False]` is clearer than `"y\nn\nn\n"`
2. **Single source of truth**: All confirms go through `ctx.console`
3. **Maintainable**: Adding/removing prompts just requires updating the list
4. **No new infrastructure**: Uses existing FakeConsole.confirm_responses

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Run `uv run pytest tests/commands/setup/init/ -v` to verify init tests specifically
3. Manually run `erk init` in a test repo to verify production behavior unchanged