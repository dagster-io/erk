---
title: Testing CLI Commands That Accept GitHub Issues
read_when:
  - "testing CLI commands that fetch GitHub issues"
  - "using fake plans in tests"
  - "testing issue parsing and validation"
---

# Testing CLI Commands That Accept GitHub Issues

## Pattern Overview

When testing CLI commands that fetch and process GitHub issues, use the `create_plan_store_with_plans()` helper to create fake plans without making real API calls.

## Implementation Pattern

### Setting Up Test Plans

```python
from tests.test_utils.plan_helpers import create_plan_store_with_plans
from erk_shared.plan_store.types import Plan
from datetime import datetime, UTC

def test_cli_with_plan_fetching():
    # Create fake plans for testing
    test_plans = {
        "5037": Plan(
            issue_number=5037,
            title="Phase 3 - `--for-plan` on Branch Create",
            body="Full plan content...",
            created_at=datetime(2026, 1, 16, tzinfo=UTC),
            state="open",
            labels=["erk-plan"],
        )
    }

    # Inject fake plan store into context
    plan_store = create_plan_store_with_plans(test_plans)
    ctx = ErkContext.for_test(plan_store=plan_store)
```

### Testing Issue Parsing

The `parse_issue_identifier()` function from `erk.cli.github_parsing` handles multiple input formats. Test your parsing with various formats to ensure robustness:

- Plain number: `"5037"`
- P-prefixed: `"P5037"`
- Full URL: `"https://github.com/dagster-io/erk/issues/5037"`

See `erk_shared.github.parsing` for the pure parsing functions, and `erk.cli.github_parsing` for CLI wrappers that raise `SystemExit` on failure.

### Testing Plan Validation

Use `prepare_plan_for_worktree()` to validate plans and derive branch names. The function returns either a setup object with the derived branch name, or an `IssueValidationFailed` object with an error message.

Key validation checks:

- Issue must have the `erk-plan` label
- Issue must have plan content in the body

### Testing Mutual Exclusivity

When adding multiple input options, always test mutual exclusivity:

```python
def test_fails_with_both_branch_and_for_plan():
    # Both arguments should cause exit
    runner = CliRunner()
    result = runner.invoke(
        branch_create_cmd,
        ["my-branch", "--for-plan", "5037"],
        obj=ctx,
    )
    assert result.exit_code == 1
    assert "Cannot specify both" in result.output


def test_fails_without_branch_or_for_plan():
    # Neither argument should cause exit
    runner = CliRunner()
    result = runner.invoke(branch_create_cmd, [], obj=ctx)
    assert result.exit_code == 1
    assert "Must provide BRANCH argument or --for-plan option" in result.output
```

### Testing `.impl/` Folder Creation

Verify the implementation folder is created with correct metadata. After invoking the command, check:

1. The `.impl/` directory exists in the worktree path
2. `plan.md` contains the plan content
3. `issue.json` contains the issue metadata (number, URL, title)

### Testing Activation Script Creation

Verify the activation script is created and its path is printed. Check:

1. The `.erk/activate.sh` file exists in the worktree
2. The output contains `source` and the script path
3. The output contains "To activate the worktree environment:"

## Layer Placement

These tests belong in **Layer 4: Business Logic Tests** because they:

- Test business logic (plan fetching, branch creation, `.impl/` setup)
- Use fake dependencies (FakeGit, fake plan store)
- Verify multiple coordinated operations (parsing + validation + folder creation)

**Location:** `tests/unit/cli/commands/branch/test_create_cmd.py`

## Key Testing Principles

1. **Use fake plans** - Never make real GitHub API calls in tests
2. **Test all input formats** - The issue identifier parser accepts multiple formats
3. **Test error cases** - Invalid labels, missing issues, validation failures
4. **Test mutual exclusivity** - Prevent conflicting options
5. **Verify side effects** - Check that `.impl/` folder and scripts are created
6. **Test the output** - Users rely on printed paths for copy-paste

## Related Topics

- [CLI Testing](cli-testing.md) - General patterns for testing erk CLI commands
- [Testing Reference](testing.md) - Overall test architecture and layer definitions
