# Migrate `track_learn_result.py` and `track_learn_evaluation.py` to PlanBackend

## Context

This plan implements **step 3.4** of objective #6864: migrating the final two learn-related exec scripts to use `PlanBackend` instead of direct `GitHubIssues` gateway calls.

### Why This Migration Matters

The current implementation violates the plan storage abstraction boundary:

- `track_learn_result.py` directly manipulates GitHub issue bodies via `update_plan_header_learn_result()` + `update_issue_body()`
- `track_learn_evaluation.py` directly manipulates GitHub issue bodies via `update_plan_header_learn_event()` + `update_issue_body()`
- Both scripts bypass `PlanBackend`, making them tightly coupled to GitHub as the plan storage provider

After migration:

- Scripts route through `PlanBackend.update_metadata()` for learn status updates
- Plan storage becomes swappable (precursor to migrating from issues to draft PRs per objective #6861)
- Error handling becomes unified (`RuntimeError` instead of multiple discriminated union types)
- Aligns with previous migrations in this objective (PRs #7005, #7046, #7033)

### Objective Context

**Objective #6864**: Consolidate Plan Operations Behind PlanBackend Abstraction

**Current Progress**: Phase 3 (Migrate Exec Scripts to PlanBackend)

| Step | Description | Status |
|------|-------------|--------|
| 3.1 | Migrate `impl_signal.py` | ✅ Done (PR #7005) |
| 3.2 | Migrate `upload_session.py`, `update_plan_remote_session.py` | ✅ Done (PR #7033) |
| 3.3 | Migrate `update_dispatch_info.py`, `mark_impl_started/ended.py` | ✅ Done (PR #7046) |
| **3.4** | **Migrate `track_learn_result.py`, `track_learn_evaluation.py`** | **← This plan** |
| 3.5 | Migrate `plan_update_issue.py`, `plan_update_from_feedback.py` | Pending |
| 3.6 | Migrate `plan_create_review_pr.py`, `plan_review_complete.py` | Pending |
| 3.7 | Migrate `handle_no_changes.py`, `get_plan_metadata.py` | Pending |

## What Changes

### Files Modified

1. **`src/erk/cli/commands/exec/scripts/track_learn_result.py`**
   - Replace `require_issues(ctx)` → `require_plan_backend(ctx)`
   - Replace `github_issues.get_issue()` + `update_plan_header_learn_result()` → `backend.update_metadata()`
   - Remove imports: `IssueNotFound`, `update_plan_header_learn_result`, `BodyText`
   - Update error handling: `isinstance(IssueNotFound)` → `except RuntimeError`
   - Preserve: Click decorators, argument/option validation, output JSON structure

2. **`src/erk/cli/commands/exec/scripts/track_learn_evaluation.py`**
   - Replace `require_issues(ctx)` → `require_plan_backend(ctx)`
   - Replace `github_issues.get_issue()` + `update_plan_header_learn_event()` → `backend.update_metadata()`
   - Remove imports: `IssueNotFound`, `update_plan_header_learn_event`, `BodyText`
   - Update error handling: `isinstance(IssueNotFound)` → `except RuntimeError`
   - Preserve: Click decorators, issue resolution logic (branch inference), output JSON structure

### Files Created

3. **`tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`**
   - Test success case: updating learn status with no plan, with plan issue, with plan PR
   - Test validation errors: missing/unexpected plan-issue, missing/unexpected plan-pr
   - Test issue not found error
   - Test JSON output structure

4. **`tests/unit/cli/commands/exec/scripts/test_track_learn_evaluation.py`**
   - Test success case: explicit issue number
   - Test success case: infer from branch name
   - Test invalid issue identifier error
   - Test no issue specified error
   - Test issue not found error
   - Test JSON output structure

## Implementation Details

### 1. Migration Pattern: track_learn_result.py

#### Before (Current Implementation)

```python
# Lines 152-179 (approximate)
github_issues = require_issues(ctx)
repo_root = require_repo_root(ctx)

# Fetch current issue body
issue_info = github_issues.get_issue(repo_root, issue)
if isinstance(issue_info, IssueNotFound):
    error = TrackLearnResultError(
        success=False,
        error="issue-not-found",
        message=f"Issue #{issue} not found",
    )
    click.echo(json.dumps(asdict(error)), err=True)
    raise SystemExit(1)

# Update metadata in body
updated_body = update_plan_header_learn_result(
    issue_body=issue_info.body,
    learn_status=status,
    learn_plan_issue=plan_issue,
    learn_plan_pr=plan_pr,
)

# Write back to GitHub
github_issues.update_issue_body(repo_root, issue, BodyText(content=updated_body))
```

#### After (Migration Target)

```python
backend = require_plan_backend(ctx)
repo_root = require_repo_root(ctx)

# Direct metadata update through PlanBackend
try:
    backend.update_metadata(
        repo_root,
        str(issue),  # plan_id is issue number as string
        metadata={
            "learn_status": status,
            "learn_plan_issue": plan_issue,
            "learn_plan_pr": plan_pr,
        },
    )
except RuntimeError as e:
    error = TrackLearnResultError(
        success=False,
        error="github-api-failed",
        message=f"Failed to update learn status on issue #{issue}: {e}",
    )
    click.echo(json.dumps(asdict(error)), err=True)
    raise SystemExit(1) from None
```

#### Key Changes Summary

| Aspect | Before | After |
|--------|--------|-------|
| Gateway | `GitHubIssues` via `require_issues()` | `PlanBackend` via `require_plan_backend()` |
| Fetch Step | `github_issues.get_issue()` | Removed (backend handles internally) |
| Update Step | `update_plan_header_learn_result()` + `update_issue_body()` | Single `backend.update_metadata()` call |
| Error Type | `IssueNotFound` discriminated union | `RuntimeError` exception |
| Error Check | `isinstance(issue_info, IssueNotFound)` | `except RuntimeError` |
| Imports Removed | `IssueNotFound`, `update_plan_header_learn_result`, `BodyText` | — |

#### Metadata Fields

```python
{
    "learn_status": str,           # One of: completed_no_plan, completed_with_plan, pending_review
    "learn_plan_issue": int | None,  # Set when status="completed_with_plan"
    "learn_plan_pr": int | None,     # Set when status="pending_review"
}
```

#### Validation Logic (Preserved)

Must preserve existing validation that enforces metadata field constraints:

- `completed_with_plan` **requires** `--plan-issue`, **forbids** `--plan-pr`
- `completed_no_plan` **forbids** both `--plan-issue` and `--plan-pr`
- `pending_review` **requires** `--plan-pr`, **forbids** `--plan-issue`

This validation happens **before** calling `backend.update_metadata()`.

### 2. Migration Pattern: track_learn_evaluation.py

#### Before (Current Implementation)

```python
# Inside _do_track() helper
github_issues = require_issues(ctx)
repo_root = require_repo_root(ctx)

# Post tracking comment
track_learn_invocation(
    github=require_github(ctx),
    time=require_time(ctx),
    issue_number=issue_number,
    session_id=session_id,
    readable_count=0,  # Always 0 in this context
    total_count=0,     # Always 0 in this context
)

# Fetch current issue body
issue_info = github_issues.get_issue(repo_root, issue_number)
if isinstance(issue_info, IssueNotFound):
    # Error handling...
    raise SystemExit(1)

# Update metadata in body
updated_body = update_plan_header_learn_event(
    issue_body=issue_info.body,
    timestamp=require_time(ctx).now_iso(),
    session_id=session_id,
)

# Write back to GitHub
github_issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
```

#### After (Migration Target)

```python
# Inside _do_track() helper
backend = require_plan_backend(ctx)
repo_root = require_repo_root(ctx)
time = require_time(ctx)

# Post tracking comment (still uses track_learn_invocation helper)
track_learn_invocation(
    github=require_github(ctx),
    time=time,
    issue_number=issue_number,
    session_id=session_id,
    readable_count=0,
    total_count=0,
)

# Update metadata through PlanBackend
try:
    backend.update_metadata(
        repo_root,
        str(issue_number),
        metadata={
            "last_learn_at": time.now_iso(),
            "last_learn_session": session_id,
        },
    )
except RuntimeError as e:
    error = TrackLearnError(
        success=False,
        error="github-api-failed",
        message=f"Failed to track learn evaluation on issue #{issue_number}: {e}",
    )
    click.echo(json.dumps(asdict(error)), err=True)
    raise SystemExit(1) from None
```

#### Key Changes Summary

| Aspect | Before | After |
|--------|--------|-------|
| Gateway | `GitHubIssues` via `require_issues()` | `PlanBackend` via `require_plan_backend()` |
| Fetch Step | `github_issues.get_issue()` | Removed (backend handles internally) |
| Update Step | `update_plan_header_learn_event()` + `update_issue_body()` | Single `backend.update_metadata()` call |
| Comment Step | `track_learn_invocation()` | **Unchanged** (still used) |
| Error Type | `IssueNotFound` discriminated union | `RuntimeError` exception |
| Error Check | `isinstance(issue_info, IssueNotFound)` | `except RuntimeError` |
| Imports Removed | `IssueNotFound`, `update_plan_header_learn_event`, `BodyText` | — |

#### Metadata Fields

```python
{
    "last_learn_at": str,           # ISO 8601 timestamp
    "last_learn_session": str | None # Claude Code session ID (optional)
}
```

#### Preserved Functionality

- **Issue resolution logic**: The `_extract_issue_number()` helper that parses explicit issue numbers or GitHub URLs remains unchanged
- **Branch inference**: The logic that calls `extract_leading_issue_number(branch_name)` when no explicit issue is provided remains unchanged
- **Tracking comment**: The `track_learn_invocation()` call that posts a metadata-block comment to the issue remains unchanged

### 3. Testing Strategy

#### Test File Structure

Both test files follow the established pattern from `test_update_dispatch_info.py` and `test_mark_impl_started_ended.py`:

```python
from pathlib import Path
from click.testing import CliRunner
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.metadata.schemas import (
    find_metadata_block,
    render_metadata_block,
)

def make_issue_info(issue_number: int, body: str) -> IssueInfo:
    """Helper to create test issue info."""
    return IssueInfo(
        number=issue_number,
        title=f"Test Issue {issue_number}",
        body=body,
        state="open",
        url=f"https://github.com/test/test/issues/{issue_number}",
        labels=[],
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )

def test_track_learn_result_completed_with_plan() -> None:
    """Test tracking learn result with completed_with_plan status."""
    # Setup: Create fake GitHub issues with plan-header block
    plan_header_block = render_metadata_block("plan-header", {
        "learn_status": "not_started",
    })
    body = f"# Test Plan\n\n{plan_header_block}\n\nPlan content..."
    fake_gh = FakeGitHubIssues(issues={123: make_issue_info(123, body)})

    # Execute: Run command with fake gateway
    runner = CliRunner()
    result = runner.invoke(
        track_learn_result,
        ["--issue", "123", "--status", "completed_with_plan", "--plan-issue", "456"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Assert: Command succeeded
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["learn_status"] == "completed_with_plan"
    assert output["learn_plan_issue"] == 456

    # Verify: Metadata was updated
    updated_issue = fake_gh.get_issue(Path(), 123)
    assert isinstance(updated_issue, IssueInfo)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["learn_status"] == "completed_with_plan"
    assert block.data["learn_plan_issue"] == 456
```

#### Test Coverage Matrix

**test_track_learn_result.py:**

| Test Case | Validates |
|-----------|-----------|
| `test_completed_no_plan` | `--status completed_no_plan` with no plan-issue/plan-pr |
| `test_completed_with_plan` | `--status completed_with_plan` with `--plan-issue` |
| `test_pending_review` | `--status pending_review` with `--plan-pr` |
| `test_missing_plan_issue` | Error when `completed_with_plan` without `--plan-issue` |
| `test_unexpected_plan_issue` | Error when `completed_no_plan` with `--plan-issue` |
| `test_missing_plan_pr` | Error when `pending_review` without `--plan-pr` |
| `test_unexpected_plan_pr` | Error when `completed_no_plan` with `--plan-pr` |
| `test_issue_not_found` | Error when issue doesn't exist |
| `test_json_output_structure` | Validates success result dataclass fields |

**test_track_learn_evaluation.py:**

| Test Case | Validates |
|-----------|-----------|
| `test_explicit_issue_number` | `--issue 123` updates metadata correctly |
| `test_explicit_github_url` | Parse `https://github.com/owner/repo/issues/123` |
| `test_infer_from_branch` | Extract issue from branch name like `P123-...` |
| `test_with_session_id` | `--session-id abc123` is recorded |
| `test_without_session_id` | `last_learn_session` is None when omitted |
| `test_invalid_issue_identifier` | Error when issue arg is malformed |
| `test_no_issue_specified` | Error when no issue and not on valid branch |
| `test_issue_not_found` | Error when issue doesn't exist |
| `test_json_output_structure` | Validates success result dataclass fields |

#### Key Testing Principles

1. **Inject fake gateways**: Use `ErkContext.for_test(github_issues=fake_gh)` to inject `FakeGitHubIssues`
2. **PlanBackend auto-wrapping**: `ErkContext.for_test()` automatically wraps `fake_gh` in `GitHubPlanStore`
3. **State verification**: Assert both command output AND verify metadata mutations via `find_metadata_block()`
4. **Use CliRunner**: Never call command functions directly; always use `runner.invoke()`
5. **Test error paths**: Verify error codes, messages, and exit codes for all failure modes

### 4. Edge Cases and Error Handling

#### RuntimeError Handling

The `PlanBackend.update_metadata()` method raises `RuntimeError` for:

- Issue not found
- Plan-header metadata block not found in issue body
- Validation errors (invalid metadata field values)
- GitHub API failures

All these error cases must be handled with a single `except RuntimeError` block that produces a unified error response.

#### Validation Order

For `track_learn_result.py`, validation happens in this order:

1. **CLI validation** (Click level): Ensure `--status` is one of the allowed enum values
2. **Script validation** (Python level): Enforce constraints between `--status`, `--plan-issue`, `--plan-pr`
3. **Backend validation** (PlanBackend level): Schema validation of metadata fields
4. **Gateway validation** (GitHub API level): Issue exists, has plan-header block

Errors at levels 1-2 exit early before calling `backend.update_metadata()`. Errors at levels 3-4 are caught as `RuntimeError`.

#### Branch Inference Edge Cases

For `track_learn_evaluation.py`, the branch inference logic must handle:

- No git repository (context initialization fails before script runs)
- Detached HEAD (no branch name available → error)
- Branch name doesn't match `P{N}-...` pattern → error "no-issue-specified"
- Branch name matches pattern but issue doesn't exist → error "issue-not-found"

The error messages must distinguish between "couldn't infer issue from branch" vs "inferred issue but it doesn't exist".

## Files NOT Changing

### Unchanged Dependencies

- **`track_learn_invocation()` helper** (`src/erk/cli/helpers/learn_tracking.py`) - Still used by `track_learn_evaluation.py` to post tracking comment. This helper calls `GitHub.add_comment()`, which is orthogonal to plan metadata updates.

- **`extract_leading_issue_number()` helper** - Still used by `track_learn_evaluation.py` for branch-based issue inference.

- **`LearnStatusValue` enum** - The set of valid learn status values remains unchanged.

### Unchanged Callers

The scripts' CLI interfaces (arguments, options, JSON output structure) remain stable, so callers don't need updates:

- `/erk:learn` skill (`.claude/skills/erk-learn/main.py`)
- Learn workflow commands
- Any CI workflows that invoke these scripts

### Files Out of Scope

The following exec scripts are NOT part of this step (they're in steps 3.5-3.7):

- `plan_update_issue.py` (step 3.5)
- `plan_update_from_feedback.py` (step 3.5)
- `plan_create_review_pr.py` (step 3.6)
- `plan_review_complete.py` (step 3.6)
- `handle_no_changes.py` (step 3.7)
- `get_plan_metadata.py` (step 3.7)

## Verification Steps

After implementation, verify:

1. **Unit tests pass**: Run `pytest tests/unit/cli/commands/exec/scripts/test_track_learn_result.py tests/unit/cli/commands/exec/scripts/test_track_learn_evaluation.py -v`

2. **Type checking passes**: Run `ty check` on both modified scripts

3. **Manual smoke test** (track_learn_result):
   ```bash
   # Create test plan issue with plan-header block
   erk exec track-learn-result --issue <test-issue> --status completed_with_plan --plan-issue 999
   # Verify: Check issue body has learn_status=completed_with_plan, learn_plan_issue=999
   ```

4. **Manual smoke test** (track_learn_evaluation):
   ```bash
   # From a branch like P123-test
   erk exec track-learn-evaluation --session-id test-session
   # Verify: Check issue 123 has last_learn_at timestamp and last_learn_session=test-session
   ```

5. **Integration test**: Run `/erk:learn` on an existing plan issue and verify it successfully tracks learn result

6. **No regressions**: Verify existing tests for learn workflows still pass

## Related PRs and Context

**Previous successful migrations in this objective:**

- **PR #7005**: Migrated `impl_signal.py` to PlanBackend
- **PR #7046**: Migrated `update_dispatch_info.py`, `mark_impl_started.py`, `mark_impl_ended.py` to PlanBackend
- **PR #7033**: Migrated `upload_session.py`, `update_plan_remote_session.py` to PlanBackend

**Reference implementations to study:**

- `src/erk/cli/commands/exec/scripts/update_dispatch_info.py` - Clean example of metadata update migration
- `src/erk/cli/commands/exec/scripts/mark_impl_started.py` - Shows timestamp metadata pattern
- `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py` - Test pattern to follow

**Documentation:**

- [Gateway vs Backend ABC Pattern](docs/learned/architecture/gateway-vs-backend.md)
- [Exec Script Patterns](docs/learned/cli/exec-script-patterns.md)
- [Learn Workflow](docs/learned/planning/learn-workflow.md)

## Success Criteria

This plan is successfully implemented when:

1. ✅ `track_learn_result.py` uses `PlanBackend.update_metadata()` instead of direct GitHub issues manipulation
2. ✅ `track_learn_evaluation.py` uses `PlanBackend.update_metadata()` instead of direct GitHub issues manipulation
3. ✅ Both scripts have comprehensive unit test coverage
4. ✅ All tests pass (new and existing)
5. ✅ Type checking passes with no new errors
6. ✅ Manual smoke tests confirm scripts work correctly
7. ✅ No imports remain from `gateway.github.metadata.plan_header` (except via `PlanBackend` internally)
8. ✅ Error handling is unified via `RuntimeError` instead of discriminated unions
9. ✅ JSON output structure and CLI interfaces remain stable (no breaking changes for callers)