# Plan: Phase 1A - PR Submit Strategy Abstraction Steelthread

**Part of Objective #5536, Phase 1A**

## Summary

Create a minimal vertical slice proving the strategy pattern works for PR submission. Implement `SubmitStrategy` ABC and `GraphiteSubmitStrategy`, wire into the Graphite path only, keeping the standard flow unchanged.

## Goal

After this PR:
- `SubmitStrategy` ABC defines the interface for PR submission strategies
- `GraphiteSubmitStrategy` encapsulates the Graphite-first flow
- `_execute_pr_submit()` uses strategy for Graphite path (standard path unchanged)
- `resolve_issue_reference()` consolidates scattered issue discovery logic
- All existing tests pass, new strategy tests added

## Files to Create

### 1. `packages/erk-shared/src/erk_shared/gateway/pr/strategy/types.py`

```python
@dataclass(frozen=True)
class SubmitStrategyResult:
    """Result from any submit strategy."""
    pr_number: int
    base_branch: str
    graphite_url: str | None  # None for core flow
    pr_url: str
    branch_name: str
    was_created: bool

@dataclass(frozen=True)
class SubmitStrategyError:
    """Error from submit strategy."""
    error_type: str
    message: str
    details: dict[str, str]
```

### 2. `packages/erk-shared/src/erk_shared/gateway/pr/strategy/abc.py`

```python
class SubmitStrategy(ABC):
    @abstractmethod
    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> Generator[ProgressEvent | CompletionEvent[SubmitStrategyResult | SubmitStrategyError]]:
        ...
```

### 3. `packages/erk-shared/src/erk_shared/gateway/pr/strategy/graphite.py`

Extract logic from `_run_graphite_first_flow()`:
- Commit uncommitted changes
- Run `gt submit`
- Query PR info from GitHub
- Compute parent branch and graphite URL
- Return `SubmitStrategyResult`

Convert `click.ClickException` to `SubmitStrategyError`.

### 4. `packages/erk-shared/src/erk_shared/gateway/pr/strategy/fake.py`

```python
@dataclass(frozen=True)
class FakeSubmitStrategy(SubmitStrategy):
    result: SubmitStrategyResult | SubmitStrategyError
    progress_messages: tuple[str, ...] = ()
```

### 5. `packages/erk-shared/src/erk_shared/gateway/pr/strategy/__init__.py`

Export: `SubmitStrategy`, `SubmitStrategyResult`, `SubmitStrategyError`, `GraphiteSubmitStrategy`, `FakeSubmitStrategy`

## Files to Modify

### 6. `src/erk/cli/commands/pr/submit_cmd.py`

**Changes:**
1. Import strategy types
2. Add `_run_strategy()` helper to consume generator
3. Replace Graphite path in `_execute_pr_submit()`:

```python
# Before (lines 106-123):
if graphite_handles_push:
    pr_number, base_branch, graphite_url = _run_graphite_first_flow(ctx, cwd, debug, force)

# After:
if graphite_handles_push:
    strategy = GraphiteSubmitStrategy()
    result = _run_strategy(ctx, cwd, strategy, debug, force)
    if isinstance(result, SubmitStrategyError):
        raise click.ClickException(result.message)
    pr_number = result.pr_number
    base_branch = result.base_branch
    graphite_url = result.graphite_url
```

4. Keep `_run_core_submit()` and standard flow UNCHANGED
5. Remove or deprecate `_run_graphite_first_flow()` (logic moved to strategy)

### 7. `packages/erk-shared/src/erk_shared/impl_folder.py`

Add `resolve_issue_reference()` function:

```python
@dataclass(frozen=True)
class ResolvedIssue:
    issue_number: int | None
    issue_url: str | None
    source: str  # "impl_folder" | "branch_name" | "none"

def resolve_issue_reference(
    impl_dir: Path,
    branch_name: str,
    repo_owner: str | None,
    repo_name: str | None,
) -> ResolvedIssue:
    """Resolve issue from .impl/issue.json or branch name pattern."""
```

This consolidates `validate_issue_linkage()` with a cleaner API. Non-breaking addition.

## Tests to Add

### 8. `packages/erk-shared/tests/unit/gateway/pr/strategy/test_graphite_strategy.py`

- Happy path: gt submit succeeds, returns SubmitStrategyResult
- Error: detached HEAD returns SubmitStrategyError
- Error: gt submit fails returns SubmitStrategyError
- Progress events are yielded correctly

### 9. `packages/erk-shared/tests/unit/gateway/pr/strategy/test_types.py`

- SubmitStrategyResult field access
- SubmitStrategyError field access
- Frozen dataclass behavior

### 10. `tests/commands/pr/test_submit_graphite_strategy.py`

- Integration: strategy error becomes click.ClickException
- Integration: strategy result flows to downstream phases

## Implementation Order

```
1. types.py (result types)
2. abc.py (strategy ABC)
3. graphite.py (GraphiteSubmitStrategy)
4. fake.py (FakeSubmitStrategy)
5. __init__.py (exports)
6. submit_cmd.py (wire in strategy)
7. impl_folder.py (resolve_issue_reference)
8-10. Tests
```

## Verification

1. **Run existing tests:**
   ```bash
   make fast-ci
   ```

2. **Manual test Graphite path:**
   - On a Graphite-tracked branch with changes
   - Run `erk pr submit`
   - Verify PR created/updated with AI-generated title/body

3. **Manual test standard path unchanged:**
   - Run `erk pr submit --no-graphite`
   - Verify identical behavior to before

## Related Documentation

- Skills to load: `dignified-python`, `fake-driven-testing`
- Patterns: BranchManager ABC in `branch_manager/abc.py`, GtKit Protocol in `gateway/gt/abc.py`