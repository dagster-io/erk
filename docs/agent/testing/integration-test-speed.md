---
title: Integration Test Speed Anti-Patterns
read_when:
  - "integration test is slow"
  - "test takes too long"
  - "pytest --durations shows slow test"
---

# Integration Test Speed Anti-Patterns

## Diagnosing Slow Tests

Use pytest's `--durations` flag to identify slow tests:

```bash
# Show 10 slowest tests
uv run pytest tests/integration/ --durations=10 -q
```

## Anti-Pattern: Running Real External Binaries

**Problem**: Integration tests that invoke real external binaries (like `claude`, `gh`, `gt`) can be extremely slow due to:

- Binary startup time
- Network calls (authentication, API requests)
- Timeouts waiting for responses

**Example of the problem**:

```python
# BAD: This actually runs the claude binary (45+ seconds)
def test_cli_integration():
    runner = CliRunner()
    result = runner.invoke(execute, ["test"])  # Uses RealClaudeCliOps internally
```

**Solution**: Use the Ops/Fake pattern for external binary calls:

```python
# GOOD: Test with fake (instant)
def test_cli_with_fake(fake_cli_ops: FakeClaudeCliOps):
    fake_cli_ops.set_next_returncode(0)
    exit_code = execute_command_impl("test", False, fake_cli_ops)
    assert exit_code == 0
```

## Anti-Pattern: Redundant Integration Tests

**Problem**: Integration tests that duplicate unit test coverage waste CI time.

**How to detect**:

1. Find your slow integration test
2. Search for unit tests covering the same functionality
3. If unit test exists with fakes → delete the integration test

**Example**:

- Integration test `test_cli_integration_with_file_not_found` (45s)
- Unit test `test_claude_cli_not_found_error_propagates` (instant)
- Same coverage → delete integration test

## When Integration Tests ARE Needed

Keep integration tests for:

- Real filesystem operations (git init, file I/O)
- Database interactions
- Cross-process communication
- Verifying actual binary behavior (smoke tests, marked slow)

## Marking Slow Tests

If you must keep a slow test, mark it:

```python
@pytest.mark.slow
def test_real_claude_binary():
    """Smoke test - runs real claude CLI."""
    ...
```

Then exclude in fast runs:

```bash
uv run pytest -m "not slow"
```
