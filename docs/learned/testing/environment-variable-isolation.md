---
title: Environment Variable Isolation in Tests
read_when:
  - "debugging systematic test failures across many test files"
  - "working with ERK_PLAN_BACKEND in tests"
  - "understanding why tests behave differently based on environment"
  - "writing tests that involve plan backend selection"
tripwires:
  - action: "debugging 100+ unexpected test failures with no obvious cause"
    warning: "Check ERK_PLAN_BACKEND first. If set to 'draft_pr' in the environment, context_for_test() in erk-shared will use DraftPRPlanBackend instead of the default, causing widespread failures in tests that expect the issue-based backend. Use monkeypatch.delenv('ERK_PLAN_BACKEND', raising=False) or env_overrides={} in fixtures."
    score: 9
---

# Environment Variable Isolation in Tests

## The `ERK_PLAN_BACKEND` Contamination Pattern

Setting `ERK_PLAN_BACKEND=draft_pr` in the shell environment causes **125+ test failures** when running the full test suite. The failures are not localized — they appear across unrelated test files because the env var affects `context_for_test()`.

### Root Cause

`context_for_test()` in `packages/erk-shared/src/erk_shared/context/testing.py` creates a test `ErkContext`. When no `plan_store` is explicitly provided, it calls `get_plan_backend()` which reads `ERK_PLAN_BACKEND` from the environment:

```python
# From testing.py:192 (approximately)
elif get_plan_backend() == "draft_pr" and not issues_explicitly_passed:
    # Creates DraftPRPlanBackend instead of the default issue-based backend
```

This means tests written assuming `github` (issue-based) backend silently get `github-draft-pr` (draft-PR) backend instead.

## Two `context_for_test()` Implementations

There are two versions of `context_for_test()`:

| Location                                                | Parameter name  | Checks `ERK_PLAN_BACKEND`? |
| ------------------------------------------------------- | --------------- | -------------------------- |
| `packages/erk-shared/src/erk_shared/context/testing.py` | `github_issues` | **Yes** — respects env var |
| Local erk (if present)                                  | `issues`        | No — ignores env var       |

The parameter name difference (`issues` vs `github_issues`) is a historical artifact. The key behavioral difference is whether `ERK_PLAN_BACKEND` affects backend selection when no `plan_store` is provided.

## Mitigations

### Option 1: `monkeypatch.delenv()` in test fixtures

```python
@pytest.fixture(autouse=True)
def clear_plan_backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)
```

Use `autouse=True` in a `conftest.py` to apply across all tests in a module.

### Option 2: Explicit `plan_store` in test context

Pass `plan_store` explicitly to `context_for_test()` to bypass env var inspection:

```python
ctx = context_for_test(
    plan_store=FakePlanStore(),  # Explicit: ignores ERK_PLAN_BACKEND
    ...
)
```

### Option 3: `env_overrides` in test fixtures (if available)

Some test infrastructure supports `env_overrides={"ERK_PLAN_BACKEND": "github"}` to force the value.

## Diagnosis Steps

If you see 100+ unexpected failures:

1. Check `echo $ERK_PLAN_BACKEND` — if it's `draft_pr`, that's the cause
2. Unset it: `unset ERK_PLAN_BACKEND`
3. Re-run the failing tests to confirm they pass
4. Add a fixture to isolate tests from the env var going forward

## Related Documentation

- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) — What draft-PR backend does
- [Fake-Driven Testing](../../.claude/skills/fake-driven-testing/) — Testing patterns
