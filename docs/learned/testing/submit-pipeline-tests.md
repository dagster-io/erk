---
title: Submit Pipeline Test Organization
read_when:
  - "adding tests for a new submit pipeline step"
  - "writing _make_state helpers for pipeline step tests"
  - "deciding what to test at the step level vs the runner level"
tripwires:
  - action: "adding a test for a new pipeline step without creating a dedicated test file"
    warning: "Each pipeline step gets its own test file in tests/unit/cli/commands/pr/submit_pipeline/. Follow the one-file-per-step convention."
  - action: "testing a pipeline step by running the full pipeline"
    warning: "Test steps in isolation by calling the step function directly. Only test_run_pipeline.py exercises the runner. Step tests pre-populate state as if prior steps succeeded."
  - action: "duplicating the _make_state helper between test files"
    warning: "Each test file has its own _make_state with step-appropriate defaults (e.g., finalize tests default pr_number=42, extract_diff tests default pr_number=None). This is intentional — different steps need different pre-conditions."
---

# Submit Pipeline Test Organization

## Why One File Per Step

<!-- Source: tests/unit/cli/commands/pr/submit_pipeline/ -->

Each pipeline step in `src/erk/cli/commands/pr/submit_pipeline.py` gets a dedicated test file in `tests/unit/cli/commands/pr/submit_pipeline/`. The internal dispatch paths (`_core_submit_flow` and `_graphite_first_flow`) each get their own file too, despite being private — they contain enough branching logic to warrant isolated testing.

**Why not one big test file?** The submit pipeline has 8 steps with 2 internal dispatch paths. A single file would exceed 500 tests. File-per-step enables focused test runs (`pytest tests/unit/.../test_finalize_pr.py`) and makes it obvious which step broke when CI fails.

**Why not test through the runner?** Step isolation requires pre-populated state as if prior steps ran. Testing through the runner means every test for step 6 implicitly depends on steps 1-5 working. When step 2 breaks, every downstream test would fail — noise that hides the real problem.

## The _make_state Convention

Every test file defines its own `_make_state()` helper that constructs `SubmitState` with defaults appropriate for that step's preconditions. This duplication is deliberate, not accidental.

**Why per-file helpers instead of a shared fixture?** Each step expects different fields to be pre-populated:

| Step under test | Key defaults in _make_state |
|---|---|
| `prepare_state` | Empty strings for branch/trunk (discovery hasn't run yet) |
| `extract_diff` | `base_branch=None` (to test error path), or `"main"` (happy path) |
| `finalize_pr` | `pr_number=42`, `title="My PR Title"`, `body="My PR body"` (steps 1-6 complete) |
| `enhance_with_graphite` | `pr_number=42`, `use_graphite=True`, `graphite_url=None` (not yet enhanced) |

A shared helper would either need step-specific default profiles (complexity for no gain) or force every test to override many fields (verbose). Per-file helpers encode "what this step assumes is already done" in their defaults.

## Runner Tests: Verifying the Pipeline Contract

<!-- Source: tests/unit/cli/commands/pr/submit_pipeline/test_run_pipeline.py -->

`test_run_pipeline.py` tests two properties of the runner, not the steps themselves:

1. **Short-circuit on first error** — Configure fakes so step 1 fails, verify no later steps execute
2. **State threading** — Configure steps 1 and 2 to succeed, verify the error from step 3 references fields populated by step 1

These tests intentionally allow early steps to fail at expected points (like `no_commits` after passing through `prepare_state` and `commit_wip`). The failure point proves state was threaded — if step 3 sees the branch name populated, step 1 ran and step 2 didn't clobber it.

## Error Path Testing: Matching Real Semantics

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, enhance_with_graphite -->
<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _graphite_first_flow -->

A subtle distinction in these tests: some steps treat errors as hard failures (returning `SubmitError`), while others treat them as graceful degradation (returning state unchanged). This mirrors the pipeline's design:

| Step | Error behavior | Why |
|---|---|---|
| `_graphite_first_flow` | `SubmitError` on failure | Graphite-first path is the primary submit mechanism — failure means nothing was pushed |
| `enhance_with_graphite` | Returns state unchanged | Enhancement is optional — the PR already exists from step 3, Graphite adds metadata |

Tests must verify the correct error behavior for each step. A test asserting `isinstance(result, SubmitError)` for `enhance_with_graphite` errors would be wrong — the step handles them gracefully.

## Anti-Patterns

**Testing internal state mutations instead of the returned state:** Pipeline steps are pure functions of `(ErkContext, SubmitState) -> SubmitState | SubmitError`. Assert on the returned state, not on intermediate gateway call counts — unless you specifically need to verify a side effect occurred (like `fake_github.added_labels` in finalize tests).

**Sharing _make_state across test files:** Seems DRY but couples unrelated tests. When finalize's preconditions change, you don't want extract_diff tests to break.

## Related Documentation

- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) — Design decisions behind the pipeline steps
- [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) — Fake configuration patterns, tracking-on-error decisions
- [State Threading Pattern](../architecture/state-threading-pattern.md) — The underlying frozen-state-threading architecture
