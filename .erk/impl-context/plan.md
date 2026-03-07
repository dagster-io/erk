# Fix Slow Unit Tests: Move to Integration + Fake Gateway for setup_cmd

## Context

Performance analysis identified several unit tests that are slow because they hit real I/O:
- `test_forward_references.py` (0.34s) — scans entire source tree
- `test_context.py` tests calling real `create_context()` (0.07–0.11s) — real git/config I/O
- `test_setup_cmd.py` (0.17–0.21s) — hits real `gh api` subprocess via `run_with_error_reporting`

The first two should be integration tests. The third needs the `gh api` and `subprocess.run` calls routed through the Codespace gateway so fakes can be injected.

## Part 1: Move `test_forward_references.py` to Integration

**Move** `tests/unit/test_forward_references.py` → `tests/integration/test_forward_references.py`

No code changes needed, just a file move. This test walks the entire `src/erk/` tree and reads every `.py` file — clearly integration-level I/O.

## Part 2: Move Real `create_context()` Tests to Integration

**From** `tests/unit/core/test_context.py`, move these 3 tests to `tests/integration/test_context.py`:
- `test_regenerate_context_updates_cwd` (calls real `create_context()`)
- `test_create_context_detects_deleted_directory` (calls real `create_context()`)
- `test_regenerate_context_detects_deleted_directory` (calls real `create_context()`)

**Keep** in `tests/unit/core/test_context.py` (already use `context_for_test()`):
- `test_regenerate_context_preserves_dry_run`
- `test_create_prompt_executor_selects_codex_when_backend_is_codex`
- `test_create_prompt_executor_selects_claude_when_backend_is_claude`
- `test_create_prompt_executor_defaults_to_claude_when_config_is_none`

## Part 3: Fix `test_setup_cmd.py` — Route Through Codespace Gateway

### 3a: Extend Codespace ABC with provisioning methods

**File:** `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`

Add two abstract methods:
```python
@abstractmethod
def get_repo_id(self, owner_repo: str) -> int:
    """Get GitHub repository database ID via REST API."""
    ...

@abstractmethod
def create_codespace(self, *, repo_id: int, machine: str, display_name: str, branch: str | None) -> str:
    """Create a codespace via REST API. Returns the gh_name."""
    ...
```

### 3b: Implement in RealCodespace

**File:** `packages/erk-shared/src/erk_shared/gateway/codespace/real.py`

Move the subprocess logic from `setup_cmd.py` into `RealCodespace`:
- `get_repo_id`: runs `gh api repos/{owner_repo} --jq .id`, returns int
- `create_codespace`: runs the `gh api --method POST /user/codespaces ...` command, parses JSON, returns `gh_name`
- These methods raise `RuntimeError` on failure (integration-layer pattern per `docs/learned/architecture/subprocess-wrappers.md`)

### 3c: Implement in FakeCodespace

**File:** `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py`

Add constructor params and implementations:
```python
def __init__(self, *, run_exit_code: int = 0, repo_id: int = 12345, created_codespace_name: str = "fake-gh-name"):
    ...

def get_repo_id(self, owner_repo: str) -> int:
    return self._repo_id

def create_codespace(self, *, repo_id: int, machine: str, display_name: str, branch: str | None) -> str:
    # Track the call for assertions, return configured name
    return self._created_codespace_name
```

### 3d: Update `setup_cmd.py`

**File:** `src/erk/cli/commands/codespace/setup_cmd.py`

1. Replace `_get_repo_id()` with `ctx.codespace.get_repo_id(owner_repo)` (wrap errors at CLI layer)
2. Replace `run_with_error_reporting(["gh", "api", "--method", "POST", ...])` with `ctx.codespace.create_codespace(...)`
3. Replace bare `subprocess.run(["gh", "codespace", "ssh", ...])` with `ctx.codespace.run_ssh_command(gh_name, "claude login")`
4. CLI-layer error handling wraps gateway `RuntimeError` into `click.echo` + `SystemExit(1)`

### 3e: Rewrite tests

**File:** `tests/unit/cli/commands/codespace/test_setup_cmd.py`

All tests now use `FakeCodespace` injected via `context_for_test(codespace=FakeCodespace(...))`. Tests can assert on:
- `fake_codespace.ssh_calls` for the login SSH call
- Constructor-configured `repo_id` and `created_codespace_name` to control flow
- No real subprocess calls at all

## Key Files

| File | Action |
|------|--------|
| `tests/unit/test_forward_references.py` | Move to `tests/integration/` |
| `tests/unit/core/test_context.py` | Extract 3 tests to `tests/integration/test_context.py` |
| `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` | Add `get_repo_id`, `create_codespace` |
| `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` | Implement new methods |
| `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` | Implement new methods |
| `src/erk/cli/commands/codespace/setup_cmd.py` | Route through `ctx.codespace` |
| `tests/unit/cli/commands/codespace/test_setup_cmd.py` | Rewrite with `FakeCodespace` |

## Verification

1. Run unit tests scoped to changed areas:
   - `uv run pytest tests/unit/core/test_context.py`
   - `uv run pytest tests/unit/cli/commands/codespace/test_setup_cmd.py`
   - `uv run pytest tests/unit/fakes/` (if fake tests exist)
2. Run integration tests for moved files:
   - `uv run pytest tests/integration/test_forward_references.py`
   - `uv run pytest tests/integration/test_context.py`
3. Run `make fast-ci` to verify no regressions
