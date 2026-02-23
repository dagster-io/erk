---
title: Environment Variable Isolation in Tests
read_when:
  - "debugging systematic test failures across many test files"
  - "working with ERK_PLAN_BACKEND in tests"
  - "understanding why tests behave differently based on environment"
  - "writing tests that involve plan backend selection"
tripwires:
  - action: "debugging 100+ unexpected test failures with no obvious cause"
    warning: "Check ERK_PLAN_BACKEND first. Although the env var is now obsolete (get_plan_backend() was deleted in PR #7971), legacy code paths in context_for_test() may still read it. Use monkeypatch.delenv('ERK_PLAN_BACKEND', raising=False) or env_overrides={} in fixtures as a defensive measure until full cleanup in objective #7911."
    score: 6
---

# Environment Variable Isolation in Tests

## The `ERK_PLAN_BACKEND` Contamination Pattern

> **Note:** After PR #7971 (objective #7911 node 1.1), the `get_plan_backend()` function was deleted and the plan backend is hardcoded to `"draft_pr"`. The `ERK_PLAN_BACKEND` environment variable is no longer read by application code. The contamination pattern described below is historical but the mitigations remain relevant until vestigial code paths are fully cleaned up in later nodes of objective #7911.

Previously, setting `ERK_PLAN_BACKEND=draft_pr` in the shell environment caused **125+ test failures** when running the full test suite.

### Root Cause

`context_for_test()` in `packages/erk-shared/src/erk_shared/context/testing.py` creates a test `ErkContext`. After PR #7971, the plan backend selection is now a tautological comparison:

```python
# From testing.py:192 (approximately) — after PR #7971
elif "draft_pr" == "draft_pr" and not issues_explicitly_passed:
    # Always takes the DraftPRPlanBackend path
```

The draft-PR path is always taken regardless of environment variables. Tests that set `ERK_PLAN_BACKEND` are now exercising dead code paths. Monkeypatching this variable has no behavioral effect.

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
