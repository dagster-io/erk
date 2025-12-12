# Unit Test Layer

This directory contains fast unit tests that run in complete isolation using in-memory fakes.

## Characteristics

- ⚡ **Fast**: ~2s for 578 tests
- 🎯 **Focused**: Test business logic in isolation
- 📦 **Isolated**: No filesystem I/O, no subprocess calls
- 💉 **Dependency-Injected**: All external dependencies provided as fakes

## Fixture Preference Hierarchy

1. **`erk_inmem_env` (PREFERRED)** - Completely in-memory, zero filesystem I/O
   - Use for testing command logic and output
   - Use for testing business logic without real directories

2. **`erk_isolated_fs_env`** - When real directories needed
   - Use for testing filesystem-dependent features
   - Creates actual temp directories with `isolated_filesystem()`

3. **`tmp_path`** - Last resort for integration tests
   - Only used in `tests/integration/` directory

## Important: Never Use Hardcoded Paths

```python
# ❌ CATASTROPHICALLY WRONG - Don't do this!
ctx = ErkContext(..., cwd=Path("/test/default/cwd"))

# ✅ CORRECT - Use fixtures
with erk_inmem_env(runner) as env:
    ctx = ErkContext(..., cwd=env.cwd)
```

Hardcoded paths cause global state pollution and test isolation failures.

## Organization by Domain

Tests are organized by the domain being tested:

- **`commands/`** - CLI command implementation tests
- **`hooks/`** - Hook system tests
- **`io/`** - File I/O and artifact loading tests
- **`kits/command/`** - Command kit tests
- **`kits/gt/`** - Graphite kit tests
- **`operations/`** - Core operations and error handling tests
- **`packaging/`** - Package configuration tests

## Best Practices

- Keep tests fast - avoid anything that touches the real filesystem or network
- Use fakes - FakeGitOps, FakeGraphiteOps, FakeClaudeCliOps are available
- Test business logic, not implementation details
- Group related tests in test classes only when testing actual classes

## References

- [Parent test documentation](../AGENTS.md) - Overview and philosophy
- [erk testing guide](https://github.com/anthropics/erk/blob/master/docs/agent/testing.md) - Comprehensive testing patterns
