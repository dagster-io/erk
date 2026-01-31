---
title: Discriminated Union Error Handling
read_when:
  - "designing return types for operations that may fail"
  - "implementing T | ErrorType patterns"
  - "handling errors without exceptions"
  - "working with GeneratedPlan, PlanGenerationError, or similar types"
tripwires:
  - action: "choosing between exceptions and discriminated unions for operation failures"
    warning: "If callers branch on the error and continue the operation, use discriminated unions. If all callers just terminate and surface the message, use exceptions. Read the 'When to Use' section."
  - action: "migrating a gateway method to return discriminated union"
    warning: "Update ALL 5 implementations (ABC, real, fake, dry_run, printing) AND all call sites AND tests. Incomplete migrations break type safety."
  - action: "accessing properties on a discriminated union result without isinstance() check"
    warning: "Always check isinstance(result, ErrorType) before accessing success-variant properties. Without type narrowing, you may access .message on a success type or .data on an error type."
---

# Discriminated Union Error Handling

A LBYL-compliant pattern for handling expected failures without exceptions. Return types are unions of success and error types, allowing callers to use `isinstance()` checks.

## The Pattern

Instead of:

```python
def fetch_data() -> Data:
    """Raises DataNotFoundError if not found."""
    ...
```

Use:

```python
def fetch_data() -> Data | DataNotFound:
    """Returns DataNotFound if not found."""
    ...
```

## Core Principle

Operations that can fail for **expected, recoverable reasons** return a discriminated union:

```python
Result = SuccessType | ErrorType
```

Callers use `isinstance()` to check which variant they received.

## When to Use

The key question is: **does the caller continue after the failure?**

Use discriminated unions when:

- The caller has **branching business logic** that continues after the failure
- The error type carries **domain-meaningful structure** (e.g., `pr_number`, `branch_name`) that callers inspect
- Multiple distinct error variants require **different handling paths**

Use exceptions when:

- All callers **terminate the operation** on failure — the error just surfaces as a message
- The error type is a **structureless `message: str` wrapper** with no domain variants
- The error propagates to a **generic error boundary** (CLI handler, top-level catch)
- No caller branches on error content beyond extracting the message

### When Exceptions Are Preferred: Worktree Operations

Worktree add/remove failures are _expected_ — but they're still better as exceptions because no caller does anything meaningful with the error beyond terminating:

```python
# All callers do the same thing: extract message and stop
result = git.worktree.add_worktree(repo_root, path, branch)
if isinstance(result, WorktreeAddError):
    raise UserFacingCliError(result.message)  # Every caller does this

# vs. exceptions — simpler, same behavior
try:
    git.worktree.add_worktree(repo_root, path, branch)
except WorktreeError as e:
    raise UserFacingCliError(str(e))
```

The discriminated union buys nothing here: no caller inspects the error type, no caller branches on the error content, and every caller terminates identically. The union just adds ceremony.

Contrast with `submit_branch` and `create_branch`, where callers _do_ branch:

```python
result = branch_mgr.submit_branch(...)
if isinstance(result, BranchAlreadyExists):
    # Continue: offer to check out the existing branch
    handle_existing_branch(result.branch_name)
elif isinstance(result, SubmitError):
    # Continue: retry with different options
    retry_submit(result)

# Git branch creation (PR #6348)
result = git_ops.create_branch(name="feature", start_point="main")
if result.type == "branch_already_exists":
    # Continue: use existing branch or prompt for new name
    logger.info(f"Branch {result.branch_name} already exists, using it")
    return result.branch_name
elif result.type == "error":
    # Terminate: unexpected git failure
    raise UserFacingCliError(f"Failed to create branch: {result.message}")
# Success case continues
return result.branch_name
```

## Examples in the Codebase

### Plan Generation

```python
@dataclass(frozen=True)
class GeneratedPlan:
    content: str
    title: str

@dataclass(frozen=True)
class PlanGenerationError:
    message: str

def generate_plan_for_step(...) -> GeneratedPlan | PlanGenerationError:
    result = executor.execute_prompt(prompt, model="haiku")
    if not result.success:
        return PlanGenerationError(message=result.error or "Unknown error")
    return GeneratedPlan(content=..., title=...)
```

### Roadmap Updates

```python
@dataclass(frozen=True)
class RoadmapUpdateResult:
    success: bool
    updated_body: str | None
    error: str | None

def update_roadmap_with_plan(...) -> RoadmapUpdateResult:
    if not result.success:
        return RoadmapUpdateResult(success=False, updated_body=None, error=...)
    return RoadmapUpdateResult(success=True, updated_body=..., error=None)
```

### Next Step Inference

```python
@dataclass(frozen=True)
class NextStepResult:
    has_next_step: bool
    step_id: str | None
    step_description: str | None
    ...

@dataclass(frozen=True)
class InferenceError:
    message: str

def infer_next_step(...) -> NextStepResult | InferenceError:
    ...
```

## Concrete Examples

### Example 1: `merge_pr` - `bool | str` to Discriminated Union

**Before** (ambiguous return type):

```python
# ABC definition
def merge_pr(self, repo_root: Path, pr_number: int, ...) -> bool | str:
    """Returns True on success, error message string on failure."""

# Caller pattern (type-unsafe)
merge_result = ops.github.merge_pr(repo_root, pr_number, ...)
if merge_result is not True:
    error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
    return f"Failed to merge: {error_detail}"
```

**After** (explicit types):

```python
# Type definitions (gateway/github/types.py)
@dataclass(frozen=True)
class MergeResult:
    """Success result from merging a PR."""
    pr_number: int

@dataclass(frozen=True)
class MergeError:
    """Error result from merging a PR. Implements NonIdealState."""
    pr_number: int
    message: str

    @property
    def error_type(self) -> str:
        return "merge-failed"

# ABC definition
def merge_pr(self, repo_root: Path, pr_number: int, ...) -> MergeResult | MergeError:
    """Returns MergeResult on success, MergeError on failure."""

# Caller pattern (type-safe)
merge_result = ops.github.merge_pr(repo_root, pr_number, ...)
if isinstance(merge_result, MergeError):
    return LandPrError(
        error_type="merge-failed",
        message=f"Failed to merge PR #{pr_number}\n\n{merge_result.message}",
    )
# Type narrowing: merge_result is now MergeResult
```

**Migration Checklist** (from PR #6294):

1. Define types in `gateway/github/types.py`
2. Update ABC signature in `gateway/github/abc.py`
3. Update all 5 implementations:
   - `real.py` - Return `MergeError` for subprocess errors
   - `fake.py` - Return union types in test implementation
   - `dry_run.py` - Return `MergeResult` for no-op
   - `printing.py` - Update signature
4. Update all call sites (3 in land workflow)
5. Update tests to check `isinstance(result, MergeError)`

### Example 2: `get_issue` - Exception to Discriminated Union (Planned)

**Before** (exception-based):

```python
def get_issue(self, issue_number: int) -> IssueDetails:
    """Raises IssueNotFoundError if issue doesn't exist."""
```

**After** (discriminated union):

```python
@dataclass(frozen=True)
class IssueInfo:
    number: int
    title: str
    body: str
    state: str

@dataclass(frozen=True)
class IssueNotFound:
    issue_number: int
    message: str

    @property
    def error_type(self) -> str:
        return "issue-not-found"

def get_issue(self, issue_number: int) -> IssueInfo | IssueNotFound:
    """Returns IssueInfo if found, IssueNotFound otherwise."""
```

This pattern is documented in PR #6304 but not yet merged to master.

### Example 3: Gateway Conversion Examples - Worktree and Branch Operations

The worktree and branch gateway methods demonstrate the full discriminated union conversion pattern across multiple gateways. These conversions follow the NonIdealState protocol pattern from `remote_ops/types.py`.

#### WorktreeAdded/WorktreeAddError - add_worktree Gateway

**Before** (exception-based):

```python
# ABC definition
def add_worktree(self, *, repo_root: Path, path: Path, branch: str) -> None:
    """Raises WorktreeAddError if worktree cannot be created."""
```

**After** (discriminated union):

```python
# Type definitions (gateway/git/worktree/types.py)
@dataclass(frozen=True)
class WorktreeAdded:
    """Success result from adding a worktree."""
    path: Path
    branch: str

@dataclass(frozen=True)
class WorktreeAddError:
    """Error result from adding a worktree. Implements NonIdealState."""
    path: Path
    branch: str
    message: str

    @property
    def error_type(self) -> str:
        return "worktree-add-failed"

# ABC definition (gateway/git/worktree/abc.py)
def add_worktree(self, *, repo_root: Path, path: Path, branch: str) -> WorktreeAdded | WorktreeAddError:
    """Returns WorktreeAdded on success, WorktreeAddError on failure."""
```

**Implementation pattern** across 5 files:

- `abc.py` - Abstract method with union return type
- `real.py` - Parse subprocess errors, return `WorktreeAddError` for failures
- `fake.py` - Check injected error first, then return success/error based on test setup
- `dry_run.py` - Always return `WorktreeAdded` (no-op)
- `printing.py` - Print operation details, return `WorktreeAdded`

**Call site pattern** (18 call sites throughout codebase):

```python
result = ops.git_worktree.add_worktree(repo_root=root, path=wt_path, branch=branch)
if isinstance(result, WorktreeAddError):
    return SetupError(
        error_type="worktree-creation-failed",
        message=f"Failed to create worktree at {wt_path}\n\n{result.message}",
    )
# Type narrowing: result is now WorktreeAdded
```

#### WorktreeRemoved/WorktreeRemoveError - remove_worktree Gateway

**Before** (exception-based):

```python
def remove_worktree(self, *, repo_root: Path, path: Path) -> None:
    """Raises WorktreeRemoveError if worktree cannot be removed."""
```

**After** (discriminated union with mixed exception handling):

```python
# Type definitions (gateway/git/worktree/types.py)
@dataclass(frozen=True)
class WorktreeRemoved:
    """Success result from removing a worktree."""
    path: Path

@dataclass(frozen=True)
class WorktreeRemoveError:
    """Error result from removing a worktree. Implements NonIdealState."""
    path: Path
    message: str

    @property
    def error_type(self) -> str:
        return "worktree-remove-failed"

# ABC definition
def remove_worktree(self, *, repo_root: Path, path: Path) -> WorktreeRemoved | WorktreeRemoveError:
    """Returns WorktreeRemoved on success, WorktreeRemoveError on failure.

    Note: Cleanup operations like 'git worktree prune' may still raise exceptions
    if they fail, as this indicates corrupted repository state.
    """
```

**Key nuance**: The main `remove_worktree` operation returns discriminated union, but cleanup operations (like `git worktree prune`) remain exception-based because their failure indicates corrupted state requiring different handling. See [gateway-specific-patterns.md](gateway-specific-patterns.md) for details on mixed exception/union handling.

**Call site pattern** (12 call sites: 4 production, 8 test):

```python
result = ops.git_worktree.remove_worktree(repo_root=root, path=wt_path)
if isinstance(result, WorktreeRemoveError):
    click.echo(f"Warning: Failed to remove worktree: {result.message}", err=True)
    return 1
# Type narrowing: result is now WorktreeRemoved
```

**LBYL violation fix**: Before this conversion, `delete_cmd.py:150-168` used `_remove_worktree_safe()` wrapper to catch exceptions - a LBYL violation. The discriminated union pattern eliminates the need for try/except wrappers.

#### BranchCreated/BranchCreateError - create_branch Gateway

**Before** (exception-based):

```python
def create_branch(self, *, repo_root: Path, branch_name: str, start_point: str) -> None:
    """Raises BranchCreateError if branch cannot be created."""
```

**After** (discriminated union):

```python
# Type definitions (gateway/git/branch/types.py)
@dataclass(frozen=True)
class BranchCreated:
    """Success result from creating a branch."""
    branch_name: str
    start_point: str

@dataclass(frozen=True)
class BranchCreateError:
    """Error result from creating a branch. Implements NonIdealState."""
    branch_name: str
    message: str

    @property
    def error_type(self) -> str:
        return "branch-create-failed"

# ABC definition (gateway/git/branch/abc.py)
def create_branch(self, *, repo_root: Path, branch_name: str, start_point: str) -> BranchCreated | BranchCreateError:
    """Returns BranchCreated on success, BranchCreateError on failure."""
```

**Multi-caller example**: `create_branch` is called from multiple contexts:

- Worktree creation workflows
- Branch management commands
- Plan implementation setup

Each caller uses the same isinstance() pattern, with context-specific error handling.

**Migration reference**: See PR #6350 (add_worktree), PR #6346 (remove_worktree) for complete conversion examples.

### 5-Place Implementation Checklist

When converting a gateway method to discriminated union:

1. **Types file**: Define `SuccessType` and `ErrorType` dataclasses with `@property error_type() -> str`
2. **ABC**: Update abstract method signature to `-> SuccessType | ErrorType`
3. **Real implementation**: Parse subprocess/API errors, return ErrorType for failures
4. **Fake implementation**: Add error injection parameters, check injected error FIRST
5. **Dry-run/Printing**: Update signatures, typically return SuccessType
6. **All call sites**: Replace try/except with `isinstance(result, ErrorType)` checks
7. **All tests**: Update to check `isinstance(result, ErrorType)` instead of catching exceptions

Cross-reference: [gateway-abc-implementation.md](gateway-abc-implementation.md) for detailed 5-place update pattern.

### Example 4: LandError - Structured Pipeline Error

The land command pipeline uses a structured error type that extends the discriminated union pattern with pipeline-specific metadata. This demonstrates how discriminated unions can encode rich error context for complex workflows.

**LandError definition** (`land_pipeline.py:82-89`):

```python
@dataclass(frozen=True)
class LandError:
    """Error result from land pipeline."""
    phase: str              # Which pipeline stage failed ('validation' or 'execution')
    error_type: str         # Machine-readable error classification
    message: str            # Human-readable description
    details: dict[str, Any] | None = None  # Optional structured context

    @property
    def error_type(self) -> str:
        return self.error_type
```

**Pipeline step signature**:

```python
LandStep = Callable[[ErkContext, LandState], LandState | LandError]
```

Each pipeline step returns either:

- Updated `LandState` to pass to next step
- `LandError` to short-circuit pipeline and propagate error to caller

**Consumer pattern in validation pipeline**:

```python
def run_validation_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run all validation steps, short-circuit on first error."""
    for step in [resolve_target, validate_checks, check_no_conflicts, ...]:
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result  # Short-circuit pipeline
        state = result  # Update state for next step
    return state
```

**Benefits of structured error**:

1. **Phase tracking**: Caller knows if error occurred in validation vs execution
2. **Machine-readable error_type**: Enables specific error handling (e.g., "pr-checks-failing" vs "merge-conflict")
3. **Structured details**: Optional dict for additional context (PR number, check names, etc.)
4. **Pipeline composition**: Each step has same signature, enabling functional composition

**Reference**: See [linear-pipelines.md](linear-pipelines.md) for complete land pipeline architecture.

## Consumer Pattern

### CLI Layer Pattern

For CLI commands consuming discriminated unions, use `UserFacingCliError`:

```python
from erk.cli.ensure import UserFacingCliError

# Check error case first and raise UserFacingCliError
push_result = ctx.git.remote.push_to_remote(repo.root, "origin", branch)
if isinstance(push_result, PushError):
    raise UserFacingCliError(push_result.message)

# Type narrowing: push_result is now PushSuccess
user_output(click.style("✓", fg="green") + " Branch pushed successfully")
```

**Why UserFacingCliError:**

- Caught at CLI entry point (`main()`) with consistent error styling
- Exits with code 1 automatically
- One-line pattern: `raise UserFacingCliError(error.message)`
- Replaces verbose two-line pattern: `user_output(error) + raise SystemExit(1)`

### Library Layer Pattern

For library code (non-CLI), check the error case and return or propagate:

```python
result = generate_plan_for_step(executor, ...)

if isinstance(result, PlanGenerationError):
    return result  # Propagate error to caller

# Type narrowing: result is now GeneratedPlan
return process_plan(result)
```

## Design Guidelines

### Error Types Should Be Frozen Dataclasses

```python
@dataclass(frozen=True)
class MyOperationError:
    message: str
    context: str | None = None  # Optional context fields
```

### Include Useful Context

Error types should include enough information for callers to handle them appropriately:

```python
@dataclass(frozen=True)
class PRNotFound:
    branch: str | None = None    # What was looked up
    pr_number: int | None = None
```

### Naming Conventions

| Convention           | Example                                   |
| -------------------- | ----------------------------------------- |
| `<Operation>Error`   | `PlanGenerationError`                     |
| `<Resource>NotFound` | `PRNotFound`, `ResourceNotFound`          |
| `<Operation>Result`  | `RoadmapUpdateResult` (with success bool) |

## Comparison with Other Patterns

### vs. Exceptions

| Discriminated Unions        | Exceptions              |
| --------------------------- | ----------------------- |
| Explicit in type signature  | Hidden control flow     |
| Caller must handle          | Can be silently ignored |
| LBYL-compliant              | EAFP approach           |
| IDE shows possible failures | Requires doc reading    |

### vs. None Return

| Discriminated Unions          | Return None          |
| ----------------------------- | -------------------- |
| Preserves error context       | Loses information    |
| Type-specific handling        | Generic "not found"  |
| Multiple error types possible | Single failure state |

### vs. Result[T, E] Generic

Some languages use `Result[T, E]` generics. Python's union syntax achieves the same with less ceremony:

```python
# Instead of Result[Data, Error]
def fetch() -> Data | Error:
    ...
```

## Exec Command Error Pattern

Exec commands (scripts in `src/erk/cli/commands/exec/scripts/`) MUST use frozen dataclass discriminated unions for their JSON output. This ensures callers get a clear contract for success and error cases.

### The Pattern

Exec commands use a three-layer approach:

1. **Custom exception type** for internal error propagation
2. **Frozen dataclass discriminated unions** for the JSON contract (Success | Error)
3. **CLI boundary conversion** that catches exceptions and converts to JSON

### Implementation Template

```python
# 1. Define the success and error dataclasses
@dataclass(frozen=True)
class MyCommandSuccess:
    """Success response for my-command."""
    success: bool
    result_field1: str
    result_field2: int
    # Include all relevant success data

@dataclass(frozen=True)
class MyCommandError:
    """Error response for my-command."""
    success: bool
    error: str      # Machine-readable error type
    message: str    # Human-readable error message

# 2. Define custom exception for internal use
class MyCommandException(Exception):
    """Exception raised during my-command execution."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message

# 3. Implementation function raises exceptions
def _my_command_impl(...) -> MyCommandSuccess:
    if something_wrong:
        raise MyCommandException(
            error="resource-not-found",
            message="The resource could not be found"
        )

    return MyCommandSuccess(
        success=True,
        result_field1="value",
        result_field2=42
    )

# 4. CLI command converts exceptions to JSON at boundary
@click.command()
def my_command(...) -> None:
    try:
        result = _my_command_impl(...)
        click.echo(json.dumps(asdict(result)))
    except MyCommandException as e:
        error = MyCommandError(
            success=False,
            error=e.error,
            message=e.message
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1) from None
```

### Why This Hybrid Approach?

This pattern combines **exceptions internally** with **discriminated unions externally**:

- **Internal exceptions**: Simplify control flow within implementation (can propagate through helper functions)
- **External discriminated unions**: Provide clear JSON contract for callers (LBYL-compliant)
- **CLI boundary conversion**: Single point where exceptions become JSON errors

Benefits:

1. **Internal code simplicity**: Helper functions can raise exceptions without needing to thread error types through
2. **Clear JSON contract**: Callers get typed `Success | Error` discriminated union via JSON
3. **LBYL for callers**: Calling code can check `success` field before accessing result fields
4. **Type safety**: Both success and error cases are frozen dataclasses with explicit fields

### Exemplar: plan_review_complete

The `plan_review_complete.py` script demonstrates this pattern:

**Success fields:**

```python
@dataclass(frozen=True)
class PlanReviewCompleteSuccess:
    success: bool
    issue_number: int
    pr_number: int
    branch_name: str
    branch_deleted: bool
    local_branch_deleted: bool
```

**Error fields:**

```python
@dataclass(frozen=True)
class PlanReviewCompleteError:
    success: bool
    error: str
    message: str
```

**CLI boundary conversion** (lines 183-191):

```python
try:
    result = _plan_review_complete_impl(...)
    click.echo(json.dumps(asdict(result)))
except PlanReviewCompleteException as e:
    error_response = PlanReviewCompleteError(
        success=False,
        error=e.error,
        message=e.message,
    )
    click.echo(json.dumps(asdict(error_response)))
    raise SystemExit(1) from None
```

### Success Field Guidelines

Success dataclasses should include all relevant data the caller needs:

- **Resource identifiers**: issue_number, pr_number, branch_name
- **Operation results**: branch_deleted, local_branch_deleted
- **Generated content**: URLs, file paths, computed values

The `success: bool` field allows generic checking before parsing specific fields.

### Error Field Guidelines

Error dataclasses should include:

- **success: bool**: Always `False`, allows generic success checking
- **error: str**: Machine-readable error type (e.g., "pr-not-found", "branch-exists")
- **message: str**: Human-readable error message for display
- **Optional context fields**: Additional data for specific error types

### Related Exec Commands

This pattern is used in:

- `plan_review_complete.py` (lines 37-64, 183-191)
- `plan_create_review_pr.py` (lines 32-57)
- Other exec scripts that need structured JSON output

## Gateway Discriminated Unions: PushResult/PullRebaseResult

Git remote operations return discriminated unions at the gateway boundary:

```python
@dataclass(frozen=True)
class PushResult:
    """Success: push completed."""

@dataclass(frozen=True)
class PushError:
    message: str

    @property
    def error_type(self) -> str:
        ...

# Return type
def push_to_remote(...) -> PushResult | PushError: ...
def pull_rebase(...) -> PullRebaseResult | PullRebaseError: ...
```

Success variants are empty marker types. Error variants contain `message` and a read-only `error_type` property for classification. See `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`.

## Pipeline Discriminated Unions: SubmitState/SubmitError

The submit pipeline threads an immutable `SubmitState` through 8 steps, where each step returns `SubmitState | SubmitError`:

```python
@dataclass(frozen=True)
class SubmitError:
    phase: str       # Which pipeline step failed
    error_type: str  # Machine-readable error classification
    message: str     # Human-readable description
    details: str | None
```

The pipeline runner short-circuits on the first `isinstance(result, SubmitError)` check. See `src/erk/cli/commands/pr/submit_pipeline.py:74-81`.

## LBYL isinstance() Pattern in Exec Commands

Exec commands use isinstance() checks after gateway calls:

```python
# From objective_roadmap_update.py
issue = ctx.github.issues.get_issue(repo_root, objective_number)
if isinstance(issue, IssueNotFound):
    # Handle error — never use try/except for this
    return error_response(...)

# Type narrowing: issue is now IssueInfo
phases, warnings = parse_roadmap(issue.body)
```

This pattern keeps LBYL principles consistent from gateway layer through exec command layer.

## Related Documentation

- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Specific pattern for lookup operations
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Gateways often use this pattern
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where exceptions become discriminated unions
- [State Threading Pattern](state-threading-pattern.md) - Pipeline discriminated union pattern
