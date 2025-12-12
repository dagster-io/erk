# Integration Test Layer

This directory contains slow integration tests that exercise real subprocess calls, actual filesystem operations, and other slow I/O.

## Characteristics

- 🐢 **Slow**: ~14s for 2 tests
- 🔧 **Real tools**: Uses actual git, subprocess, and filesystem operations
- 🧪 **End-to-end**: Tests CLI interactions and edge cases
- 🔒 **Isolated**: Completely separate from fast unit tests

## When to Add Integration Tests

Add an integration test when:

- **Testing CLI interactions** that require running actual binaries
- **Testing shell quoting edge cases** that are difficult to fake accurately
- **Testing real subprocess behavior** that mocks can't capture
- **Testing filesystem interactions** that need actual directory operations

## When NOT to Add Integration Tests

DO NOT add integration tests for:

- ❌ Business logic testing (use unit tests with fakes)
- ❌ Functions that can be tested with injected fakes
- ❌ Any test that CAN run in ~10ms or less with unit-level fixtures

The goal is keeping these tests few and isolated.

## Existing Integration Tests

### `kits/gt/test_submit_branch_integration.py`

Tests real git repository operations for edge cases:

- **`test_amend_commit_with_backticks_direct`** - Tests commit message formatting with backticks using real git repo
  - Duration: ~7.5s
  - Reason: Tests shell quoting behavior difficult to fake accurately

### `kits/command/test_execute_integration.py`

Tests CLI interactions with actual subprocess execution:

- **`test_cli_integration_with_file_not_found`** - Tests error handling when running the claude binary
  - Duration: ~6.65s
  - Reason: Actually runs the claude binary via subprocess

## Best Practices

- Keep tests here minimal - only when fakes truly can't work
- Use `tmp_path` fixture for filesystem operations
- Use `runner.isolated_filesystem()` for Click CLI testing
- Document why the test needs to be integration-level
- Keep integration tests completely separate from fast unit tests

## Running Integration Tests

```bash
# Run only integration tests
pytest packages/erk-kits/tests/integration/

# Don't run these with fast unit tests in CI
# They add 14+ seconds to test feedback
```

## References

- [Parent test documentation](../AGENTS.md) - Overview and philosophy
- [erk testing guide](https://github.com/anthropics/erk/blob/master/.erk/docs/agent/testing.md) - Comprehensive testing patterns
