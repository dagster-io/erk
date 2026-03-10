# Plan: Address PR #9159 Review Comments

## Context

PR #9159 "Add `erk exec debug-impl-run` command" received automated review feedback. 11 actionable items across 2 batches. The user wants the @patch refactor done via a new `GitHubActions` sub-gateway (like `GitHubIssues`), kept separate from the main `LocalGitHub` gateway.

## Batch 1: Local Fixes (auto-proceed)

**Item #1** — `debug_impl_run.py:104`: Replace `if not line.strip(): continue` with positive logic `if line.strip():`.

**Item #2** — `impl_run_parser.py:268`: Replace `if not line.strip(): return None` with positive logic.

**Item #3** — `impl_run_parser.py:270`: LBYL for JSON parsing — **FALSE POSITIVE**. JSON parsing is an accepted exception (4 other instances in `src/erk/core/` use `try/except json.JSONDecodeError` with `# Parse JSON safely - JSON parsing requires exception handling`). Resolve thread with explanation.

## Batch 2: GitHubActions Sub-Gateway (user confirmed)

Create a `GitHubActions` sub-gateway following the `GitHubIssues` pattern.

### Step 1: Create the sub-gateway (4-file pattern)

**`packages/erk-shared/src/erk_shared/gateway/github/actions/__init__.py`** — empty

**`packages/erk-shared/src/erk_shared/gateway/github/actions/abc.py`** — ABC with 2 methods:
```python
class GitHubActions(ABC):
    @abstractmethod
    def get_run_jobs(self, repo_root: Path, *, run_id: str) -> str: ...

    @abstractmethod
    def get_job_logs(self, repo_root: Path, *, job_id: str) -> str | None: ...
```

**`packages/erk-shared/src/erk_shared/gateway/github/actions/real.py`** — `RealGitHubActions`:
- Constructor: `__init__(self, target_repo: str | None)`
- Move the `gh api` subprocess calls from `_find_implement_job` and `_fetch_job_logs` here
- Use `run_subprocess_with_context` like `RealGitHubIssues`

**`packages/erk-shared/src/erk_shared/gateway/github/actions/dry_run.py`** — `DryRunGitHubActions`:
- Both methods are read-only, so delegate to wrapped implementation

### Step 2: Create the fake

**`tests/fakes/gateway/github_actions.py`** — `FakeGitHubActions`:
- Constructor params: `run_jobs: dict[str, str]`, `job_logs: dict[str, str | None]`
- `get_run_jobs` returns from `run_jobs` dict keyed by run_id
- `get_job_logs` returns from `job_logs` dict keyed by job_id

### Step 3: Compose into LocalGitHub

**`packages/erk-shared/src/erk_shared/gateway/github/abc.py`** — add abstract property:
```python
@property
@abstractmethod
def actions(self) -> GitHubActions: ...
```

**`packages/erk-shared/src/erk_shared/gateway/github/real.py`** — `RealLocalGitHub`:
- Add `actions: GitHubActions` constructor param
- Add `actions` property

**`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`** — `DryRunLocalGitHub`:
- Wrap with `DryRunGitHubActions(wrapped.actions)`

**`tests/fakes/gateway/github.py`** — `FakeLocalGitHub`:
- Add `actions_gateway: GitHubActions | None = None` constructor param
- Default to `FakeGitHubActions()` if not provided

### Step 4: Wire into context

**`packages/erk-shared/src/erk_shared/context/helpers.py`** — add `require_actions(ctx)` helper

**`tests/fakes/tests/shared_context.py`** — add `github_actions: GitHubActions | None = None` param to `context_for_test()`

### Step 5: Refactor the command

**`src/erk/cli/commands/exec/scripts/debug_impl_run.py`**:
- Remove `_find_implement_job` and `_fetch_job_logs` (logic moves to gateway)
- Use `require_actions(ctx)` to get the gateway
- Keep `_extract_run_id` (pure function, stays)

### Step 6: Update tests

**`tests/unit/cli/commands/exec/scripts/test_debug_impl_run.py`**:
- Remove all `@patch` usage
- Use `context_for_test(github_actions=FakeGitHubActions(...))` instead
- `TestFindImplementJob` class → test the `get_run_jobs` + parsing in the command
- `TestDebugImplRunCli` class → inject `FakeGitHubActions` with pre-configured job data

## Files to Modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/debug_impl_run.py` | Refactor to use gateway, fix positive logic |
| `src/erk/core/impl_run_parser.py` | Fix positive logic, resolve LBYL false positive |
| `packages/erk-shared/src/erk_shared/gateway/github/actions/__init__.py` | NEW — empty |
| `packages/erk-shared/src/erk_shared/gateway/github/actions/abc.py` | NEW — GitHubActions ABC |
| `packages/erk-shared/src/erk_shared/gateway/github/actions/real.py` | NEW — RealGitHubActions |
| `packages/erk-shared/src/erk_shared/gateway/github/actions/dry_run.py` | NEW — DryRunGitHubActions |
| `packages/erk-shared/src/erk_shared/gateway/github/abc.py` | Add `actions` property |
| `packages/erk-shared/src/erk_shared/gateway/github/real.py` | Compose RealGitHubActions |
| `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py` | Compose DryRunGitHubActions |
| `packages/erk-shared/src/erk_shared/context/helpers.py` | Add `require_actions()` |
| `tests/fakes/gateway/github_actions.py` | NEW — FakeGitHubActions |
| `tests/fakes/gateway/github.py` | Add `actions_gateway` param |
| `tests/fakes/tests/shared_context.py` | Add `github_actions` param |
| `tests/unit/cli/commands/exec/scripts/test_debug_impl_run.py` | Replace @patch with fakes |

## Verification

1. `pytest tests/unit/cli/commands/exec/scripts/test_debug_impl_run.py -xvs`
2. `pytest tests/unit/core/test_impl_run_parser.py -xvs`
3. `make fast-ci`
4. Resolve all 11 threads via `erk exec resolve-review-threads`
5. Push and verify CI passes
