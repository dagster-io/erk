# Plan: Eliminate Exceptions from Graphite `submit_stack` (Objective #9324, Phase 1)

## Context

Objective #9324 aims to eliminate exceptions as control flow from gateway methods. Phase 1 targets `submit_stack` in the Graphite gateway — the method currently raises `RuntimeError` on failure, and callers parse error message strings to distinguish failure modes (restack required, nothing to submit, generic failure). This is fragile and not self-documenting.

The codebase already has a well-established discriminated union pattern (e.g., `PushResult | PushError`, `BranchCreated | BranchAlreadyExists`) using frozen dataclasses with `NonIdealState` protocol and `EnsurableResult` mixin.

## Node 1.1: Define Discriminated Union Types

**File:** `packages/erk-shared/src/erk_shared/gateway/graphite/types.py` (add to existing file)

Define 4 types to eliminate all string parsing at call sites:

```python
@dataclass(frozen=True)
class SubmitStackResult(EnsurableResult):
    """Stack submitted successfully."""

@dataclass(frozen=True)
class SubmitStackNothingToSubmit:
    """Benign: stack had no changes to submit. Callers may treat as success."""

@dataclass(frozen=True)
class SubmitStackRestackRequired(NonIdealStateMixin):
    """Stack has conflicts requiring manual restack before submit."""
    message: str

    @property
    def error_type(self) -> str:
        return "restack-required"

@dataclass(frozen=True)
class SubmitStackError(NonIdealStateMixin):
    """Generic submit_stack failure (timeout, exit code, etc.)."""
    message: str

    @property
    def error_type(self) -> str:
        return "submit-failed"
```

**Why 4 types instead of 2:** Call sites currently branch on 3 distinct outcomes beyond success: (a) "restack" in error → custom user guidance, (b) "nothing to submit" → treat as success, (c) generic failure. Separate types make these branches type-safe with no string parsing.

**Type alias** (in same file):
```python
SubmitStackOutcome = SubmitStackResult | SubmitStackNothingToSubmit | SubmitStackRestackRequired | SubmitStackError
```

## Node 1.2: Update ABC, Real, Fake, DryRun, Disabled

### ABC (`gateway/graphite/abc.py:136-161`)
- Change return type from `None` to `SubmitStackOutcome`
- Remove `Raises: RuntimeError` from docstring

### Real (`gateway/graphite/real.py:224-276`)
- Remove `raise RuntimeError(...)` calls
- Convert subprocess exceptions to return values:
  - `TimeoutExpired` → `SubmitStackError(message="gt submit timed out...")`
  - `CalledProcessError` with "restack" in stderr → `SubmitStackRestackRequired(message=...)`
  - `CalledProcessError` with "nothing to submit"/"no changes" in stderr → `SubmitStackNothingToSubmit()`
  - `CalledProcessError` other → `SubmitStackError(message=...)`
  - Success → `SubmitStackResult()`

### Fake (`tests/fakes/gateway/graphite.py:205-217`)
- Change `submit_stack_raises: Exception | None` constructor param to `submit_stack_result: SubmitStackOutcome` defaulting to `SubmitStackResult()`
- Return the configured result instead of raising
- Update all test call sites that pass `submit_stack_raises=RuntimeError(...)`:
  - `test_graphite_first_flow.py:94` → `submit_stack_result=SubmitStackError(message="gt submit failed")`
  - `test_graphite_first_flow.py:118` → `submit_stack_result=SubmitStackRestackRequired(message="...")`
  - `test_enhance_with_graphite.py:151` → `submit_stack_result=SubmitStackError(message="network timeout")`
  - `test_enhance_with_graphite.py:214` → `submit_stack_result=SubmitStackNothingToSubmit()`
  - `fake_ops.py:531,640` → convert error param to appropriate result type

### DryRun (`gateway/graphite/dry_run.py:61-71`)
- Return `SubmitStackResult()` instead of `None`

### Disabled (`gateway/graphite/disabled.py:84-94`)
- Return `SubmitStackError(message=f"Graphite is disabled: {self.reason}")` instead of raising `GraphiteDisabledError`
- **Note:** This changes behavior — disabled sentinel currently raises a different exception type. Callers that catch `GraphiteDisabledError` separately need checking. Search for `GraphiteDisabledError` catch blocks.

## Node 1.3: Migrate Call Sites in submit_pipeline.py

### Call site 1: `push_and_create_pr` (submit_pipeline.py:323-350)
```python
# Before: try/except with string parsing
# After:
result = ctx.graphite.submit_stack(...)
if isinstance(result, SubmitStackRestackRequired):
    return SubmitError(phase="push_and_create_pr", error_type="graphite_restack_required", ...)
if isinstance(result, (SubmitStackError, SubmitStackNothingToSubmit)):
    return SubmitError(phase="push_and_create_pr", error_type="graphite_submit_failed", ...)
```

### Call site 2: `enhance_with_graphite` (submit_pipeline.py:756-775)
```python
# Before: try/except with string parsing for "nothing to submit"
# After:
result = ctx.graphite.submit_stack(...)
if isinstance(result, SubmitStackNothingToSubmit):
    click.echo(click.style("   PR already up to date with Graphite", fg="green"))
    click.echo("")
    return state
if isinstance(result, (SubmitStackRestackRequired, SubmitStackError)):
    return SubmitError(phase="enhance_with_graphite", error_type="graphite_enhance_failed", ...)
```

### Call site 3: `branch_manager/graphite.py:184-191` (bonus — not in submit_pipeline.py)
```python
# Before: try/except converting to SubmitBranchError
# After:
result = self.graphite.submit_stack(...)
if isinstance(result, SubmitStackResult):
    return SubmitBranchResult()
return SubmitBranchError(message=result.message if hasattr(result, 'message') else "Unknown error")
```

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/graphite/types.py` | Add 4 new types + type alias |
| `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` | Change return type |
| `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` | Return values instead of raising |
| `packages/erk-shared/src/erk_shared/gateway/graphite/dry_run.py` | Return `SubmitStackResult()` |
| `packages/erk-shared/src/erk_shared/gateway/graphite/disabled.py` | Return error instead of raising |
| `tests/fakes/gateway/graphite.py` | Replace `raises` param with `result` param |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Migrate 2 try/except to isinstance |
| `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py` | Migrate try/except to isinstance |
| `tests/unit/cli/commands/pr/submit_pipeline/test_graphite_first_flow.py` | Update fake construction |
| `tests/unit/cli/commands/pr/submit_pipeline/test_enhance_with_graphite.py` | Update fake construction |
| `tests/unit/gateways/gt/fake_ops.py` | Update fake construction |
| `tests/unit/gateways/graphite/test_graphite_disabled.py` | Update disabled test expectations |

## Verification

1. Run `uv run pytest tests/unit/cli/commands/pr/submit_pipeline/` — submit pipeline tests pass
2. Run `uv run pytest tests/unit/gateways/graphite/` — disabled gateway tests pass
3. Run `uv run pytest tests/unit/gateways/gt/` — gt operations tests pass
4. Run `uv run pytest tests/real/test_real_graphite.py` — real graphite tests pass
5. Run `uv run ty check` — type checker passes
6. Run `uv run ruff check` — linter passes
