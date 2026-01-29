---
title: Hook Testing Patterns
read_when:
  - "writing tests for a PreToolUse hook"
  - "testing hooks that read from stdin"
  - "testing hook exit code behavior"
tripwires:
  - action: "creating a PreToolUse hook"
    warning: "Test against edge cases. Untested hooks fail silently (exit 0, no output). Read docs/learned/testing/hook-testing.md first."
---

# Hook Testing Patterns

Hooks that fail silently (exit 0, no output) are invisible failures. Comprehensive testing is essential because there is no runtime error signal when a hook malfunctions.

## Architecture: Pure Functions + Integration Tests

Structure hook code as pure functions with a thin orchestration layer:

1. **Pure functions** — Extract data, detect conditions, build output. Independently testable with zero dependencies.
2. **Integration entry point** — Orchestrates pure functions with I/O (stdin, capabilities, click.echo). Tested with CliRunner.

This separation enables fast, focused unit tests for logic while integration tests verify the full hook pipeline.

## Pure Function Testing (Layer 3)

Test each pure function independently with no mocking:

- **Extraction functions**: Test valid input, missing keys, wrong types, empty strings, null values
- **Detection functions**: Test positive match, negative match, edge cases (None input, empty string, similar-but-wrong extensions)
- **Output builders**: Test that output contains required keywords/phrases

Key edge cases for stdin JSON extraction:

- Empty string input
- Whitespace-only input
- Missing expected keys
- Non-dict where dict expected
- Non-string where string expected
- Empty string values

See `tests/unit/cli/commands/exec/scripts/test_pre_tool_use_hook.py` for the canonical example with 14 pure function tests.

## Integration Testing (Layer 4)

Use CliRunner with ErkContext injection to test the full hook pipeline:

```python
runner = CliRunner()
ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
stdin_data = json.dumps({
    "session_id": "test-session",
    "tool_input": {"file_path": "/src/foo.py"},
})
result = runner.invoke(hook_command, input=stdin_data, obj=ctx)
```

**Key integration scenarios**:

- **Positive case**: All conditions met → verify output contains expected content, exit code 0
- **Wrong file type**: Condition not met → verify empty output, exit code 0
- **Missing capability**: Feature not installed → verify silent, exit code 0
- **Outside project**: Not an erk project → verify silent, exit code 0
- **Missing stdin data**: No file_path in input → verify silent, exit code 0

## Capability Setup in Tests

When hooks check for installed capabilities, set up the state file in `tmp_path`:

```python
state_path = tmp_path / ".erk" / "state.toml"
state_path.parent.mkdir(parents=True, exist_ok=True)
```

Use `tomli_w.dump()` to write the state file with required capability flags. See the test file for the `_setup_dignified_python_reminder()` helper pattern.

## Stdin JSON Format

PreToolUse hooks receive this structure on stdin:

```json
{
  "session_id": "...",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file",
    "content": "..."
  }
}
```

Fields in `tool_input` vary by tool. Always use LBYL to check each level exists before accessing.

## Common Mistakes

- **Not testing empty/missing stdin**: Hooks receive empty stdin in some edge cases
- **Not testing non-erk projects**: Hooks fire in all projects, not just erk
- **Testing only the happy path**: Silent failures are the default, so negative tests are more important than positive ones
- **Using monkeypatch instead of ErkContext**: Use `ErkContext.for_test()` with CliRunner

## Reference

- Canonical example: `tests/unit/cli/commands/exec/scripts/test_pre_tool_use_hook.py`
- Hook implementation: `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py`
- Hook decorator: `src/erk/hooks/decorators.py`
