---
title: Submit Pipeline Test Organization
read_when:
  - "adding tests for submit pipeline steps"
  - "understanding how pipeline steps are tested in isolation"
  - "working with tests/unit/cli/commands/pr/submit_pipeline/"
tripwires:
  - action: "adding a test for a new pipeline step without creating a dedicated test file"
    warning: "Each pipeline step gets its own test file in tests/unit/cli/commands/pr/submit_pipeline/. Follow the one-file-per-step convention."
---

# Submit Pipeline Test Organization

The submit pipeline tests follow a one-file-per-step convention, enabling isolated testing of each pipeline step with fake dependencies.

## Directory Structure

```
tests/unit/cli/commands/pr/submit_pipeline/
├── __init__.py
├── test_commit_wip.py           # Step 2: Commit uncommitted changes
├── test_core_submit_flow.py     # Step 3 (core path): git push + gh pr create
├── test_graphite_first_flow.py  # Step 3 (Graphite path): gt submit
├── test_extract_diff.py         # Step 4: Get PR diff
├── test_enhance_with_graphite.py # Step 7: Add stack metadata
├── test_finalize_pr.py          # Step 8: Update PR metadata
├── test_prepare_state.py        # Step 1: Discovery
└── test_run_pipeline.py         # Pipeline runner integration
```

## Testing Pattern

Each test file tests one step function in isolation:

1. **Construct fake context** with configured gateways
2. **Build initial SubmitState** with fields from prior steps pre-populated
3. **Call the step function** directly
4. **Assert on the returned state or error**:
   - Success: Check that `dataclasses.replace()` added expected fields
   - Error: Check `isinstance(result, SubmitError)` and error details

## Fake Dependency Pattern

Steps consume gateways through `ErkContext`. Tests inject fakes:

```python
# Configure fakes for the specific step being tested
fake_git = FakeGit()
fake_github = FakeGitHub(pr_data=[...])
ctx = create_fake_context(git=fake_git, github=fake_github)

# Pre-populate state as if prior steps ran
state = SubmitState(cwd=tmp_path, branch_name="feature", ...)

# Call the step under test
result = extract_diff(ctx, state)
assert isinstance(result, SubmitState)
assert result.diff_file is not None
```

## Pipeline Runner Tests

`test_run_pipeline.py` tests the runner itself:

- Verifies steps execute in order
- Verifies short-circuit on first `SubmitError`
- Tests with both Graphite and core paths

## Related Documentation

- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) — Pipeline steps and types
- [Gateway Fake Testing Exemplar](gateway-fake-testing-exemplar.md) — Fake configuration patterns
- [State Threading Pattern](../architecture/state-threading-pattern.md) — Underlying architecture
