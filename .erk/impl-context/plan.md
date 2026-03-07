# Plan: Codespace connect checks out local branch

## Context

When running `erk codespace connect`, the remote codespace may be on a different branch than the local machine. The user wants the connect command to automatically check out the same branch that is currently checked out locally, so the codespace is immediately working on the right code.

## Approach

Inject `git fetch origin <branch> && git checkout <branch>` into the remote command string, before the existing `git pull` step. This keeps it as a single SSH connection.

Use `ctx.git.branch.get_current_branch(ctx.repo_root)` to get the current local branch name. If `None` (detached HEAD), skip the checkout — proceed with existing behavior.

## Files to modify

### 1. `src/erk/cli/commands/codespace/connect_cmd.py`

After resolving the codespace (line 57), get the local branch and build a checkout prefix:

```python
local_branch = ctx.git.branch.get_current_branch(ctx.repo_root)
if local_branch is not None:
    checkout_prefix = f"git fetch origin {shlex.quote(local_branch)} && git checkout {shlex.quote(local_branch)} && "
else:
    checkout_prefix = ""
```

Insert `checkout_prefix` into the remote command in both paths:

- **Non-shell** (line 74): Change `setup` to `f"{checkout_prefix}git pull && uv sync && source .venv/bin/activate"`
- **Shell** (lines 69-72): Add `checkout_prefix` alongside `cd_prefix` and `export_prefix` in the `bash -l -c` command. The condition on line 69 becomes `if export_prefix or cd_prefix or checkout_prefix`.

### 2. `tests/unit/cli/commands/codespace/test_connect_cmd.py`

Tests need `FakeGit(current_branches={repo_root: "feature-x"})` and a `RepoContext(root=repo_root, ...)` passed to `context_for_test`. The default `NoRepoSentinel` won't work since `ctx.repo_root` would raise.

Add 3 tests:

- **`test_connect_checks_out_local_branch`** — FakeGit with branch `"feature-x"`, verify remote command contains `git fetch origin feature-x && git checkout feature-x`
- **`test_connect_skips_checkout_when_detached_head`** — FakeGit with `None` branch, verify no `git fetch`/`git checkout` in remote command
- **`test_connect_shell_checks_out_local_branch`** — Same as first but with `--shell`, verify checkout appears before `exec bash -l`

Existing tests pass `NoRepoSentinel` (the default) — they still work because `get_current_branch` returns `None` for unknown paths in FakeGit, so `checkout_prefix` will be `""`. **Wait** — actually `ctx.repo_root` will raise `RuntimeError` on `NoRepoSentinel`. Need to move the `get_current_branch` call to be guarded:

```python
if isinstance(ctx.repo, NoRepoSentinel):
    local_branch = None
else:
    local_branch = ctx.git.branch.get_current_branch(ctx.repo_root)
```

This keeps existing tests passing without modification.

## Verification

1. Run `uv run pytest tests/unit/cli/commands/codespace/test_connect_cmd.py`
2. Verify all existing tests still pass
3. Verify new tests pass
