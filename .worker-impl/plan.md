# Plan: Remove duplication in worktree creation post-setup

## Problem

The `erk wt create` command has duplicate post-setup logic:

1. **`run_post_worktree_setup()`** (lines 37-67): .env + activation script + post-commands
2. **Main `create_wt()` body** (lines 853-936): Same logic inlined with extra guards

The differences in `create_wt()`:
- `--no-post` flag support (skips post-commands)
- JSON output mode suppression
- `.impl` folder creation happens between file setup and commands

## Approach: Extract file setup, keep command logic separate

Extract a new `setup_worktree_files()` function for .env + activation script only. This lets `create_wt()` use the shared helper while keeping its own command execution logic with flag support.

## Changes

**File:** `src/erk/cli/commands/wt/create_cmd.py`

### 1. Create new helper function (after imports, ~line 35)

```python
def setup_worktree_files(
    *,
    config: LoadedConfig,
    worktree_path: Path,
    repo_root: Path,
    name: str,
) -> None:
    """Write .env and activation script to worktree."""
    env_content = make_env_content(
        config, worktree_path=worktree_path, repo_root=repo_root, name=name
    )
    if env_content:
        env_path = worktree_path / ".env"
        env_path.write_text(env_content, encoding="utf-8")

    write_worktree_activate_script(worktree_path=worktree_path)
```

### 2. Refactor `run_post_worktree_setup()` to use the helper

```python
def run_post_worktree_setup(
    ctx: ErkContext,
    *,
    config: LoadedConfig,
    worktree_path: Path,
    repo_root: Path,
    name: str,
) -> None:
    """Run post-worktree setup: files and commands."""
    setup_worktree_files(
        config=config,
        worktree_path=worktree_path,
        repo_root=repo_root,
        name=name,
    )

    if config.post_create_commands:
        run_commands_in_worktree(
            ctx=ctx,
            commands=config.post_create_commands,
            worktree_path=worktree_path,
            shell=config.post_create_shell,
        )
```

### 3. Refactor `create_wt()` inline logic (~line 853-936)

Replace the duplicated .env + activation script code with:

```python
    # Write .env and activation script
    setup_worktree_files(
        config=cfg,
        worktree_path=wt_path,
        repo_root=repo.root,
        name=name,
    )

    # Create impl folder if plan file provided
    # ... [.impl logic stays the same] ...

    # Post-create commands (with --no-post and JSON mode support)
    if not no_post and cfg.post_create_commands:
        if not output_json:
            user_output("Running post-create commands...")
        run_commands_in_worktree(
            ctx=ctx,
            commands=cfg.post_create_commands,
            worktree_path=wt_path,
            shell=cfg.post_create_shell,
        )
```

## Verification

1. Run `pytest tests/unit/cli/test_activation.py -v`
2. Run `pytest tests/commands/test_create.py -v`
3. Manual test: `erk wt create test-refactor` and verify `.erk/activate.sh` exists