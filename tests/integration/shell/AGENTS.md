# Shell Integration Testing Patterns

## Purpose

Integration tests for shell command execution and script generation that involve
subprocess calls or testing behavior that will be executed by an actual shell.

## What Goes Here

Tests that verify:

- Shell wrapper scripts execute correctly in actual shells
- Commands that invoke subprocess calls to external tools
- Shell-specific behavior (bash vs fish vs zsh)
- Script generation produces valid shell syntax
- CWD recovery works with real directory changes

## Key Characteristics

✅ Tests invoke actual CLI commands through `CliRunner`
✅ Tests verify generated scripts would work in real shells
✅ Tests may read/execute generated script files
✅ Tests validate shell-specific syntax (bash, fish, zsh)

## Testing Pattern

```python
from pathlib import Path
from click.testing import CliRunner
from erk.cli.cli import cli

def test_shell_integration_sync_generates_posix_passthrough_script(tmp_path: Path) -> None:
    """When invoked from bash/zsh, __shell should return a passthrough script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["__shell", "sync"], env={"ERK_SHELL": "bash"})
    assert result.exit_code == 0
    script_output = result.output.strip()
    assert script_output
    script_path = Path(script_output)
    try:
        content = script_path.read_text(encoding="utf-8")
        assert "command erk sync" in content
        assert "__erk_exit=$?" in content
    finally:
        script_path.unlink(missing_ok=True)
```

## Why These Are Integration Tests

While these tests use `CliRunner` (which is typically for unit tests), they are
categorized as integration tests because:

1. **Testing real shell behavior**: Verifying generated scripts work in actual shells
2. **File I/O operations**: Reading/validating script files written to filesystem
3. **Subprocess boundary**: Testing the integration layer that will invoke subprocesses
4. **Shell-specific syntax**: Validating syntax that will be evaluated by real shells

## Distinction from Unit Tests

**Unit tests** (`tests/commands/shell/`):

- Test shell utility functions
- Test CWD recovery logic
- Use fakes for subprocess interactions
- No file I/O for script generation

**Integration tests** (`tests/integration/shell/`):

- Test \_\_shell handler that generates scripts
- Verify script file contents
- Test cross-command invocation via \_\_shell
- Validate shell-specific behavior

## See Also

- `tests/commands/shell/AGENTS.md` - Shell command unit test patterns
- `tests/integration/AGENTS.md` - General integration testing patterns
- `docs/learned/testing.md` - Complete testing guide
