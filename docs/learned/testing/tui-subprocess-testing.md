---
title: TUI Subprocess Testing Patterns
read_when:
  - "testing TUI features that use subprocess.Popen"
  - "writing tests for background worker methods"
  - "creating fake subprocess objects for TUI tests"
tripwires:
  - action: "monkeypatching erk.tui.app.subprocess.Popen"
    warning: "Monkeypatch subprocess.Popen at module level (subprocess.Popen), not erk.tui.app.subprocess.Popen. The import uses 'import subprocess' not 'from subprocess import Popen'."
  - action: "testing subprocess-based TUI workers without capturing status bar updates"
    warning: "Use app.call_from_thread assertions to verify status bar updates from background workers. Status bar updates are the primary user-facing output."
---

# TUI Subprocess Testing Patterns

Patterns for testing TUI features that run subprocesses in background threads.

## \_FakePopen Pattern

A minimal `subprocess.Popen` substitute for testing background workers that stream output.

**Location:** `tests/tui/test_app.py`

**Source:** `_FakePopen` class in `tests/tui/test_app.py`

### Key Design Choices

- **`return_code` parameter**: Configure success/failure per test
- **`output_lines`**: Optional list of output lines (newlines appended automatically)
- **`**kwargs`**: Accepts and ignores extra subprocess kwargs (`bufsize`, `text`, `stdin`, etc.)
- **`__iter__`**: Supports `for line in proc.stdout:` iteration pattern used by `_land_pr_async`

## Conditional Subprocess Testing

For operations that conditionally run subprocesses (e.g., objective update after landing), use the 4-test pattern:

1. **Called test**: Verify subprocess is called when condition is met
2. **Skipped test**: Verify subprocess is NOT called when condition is absent
3. **Success test**: Verify behavior when subprocess succeeds
4. **Failure test**: Verify behavior when subprocess fails (non-zero return code)

## Monkeypatch Target

The correct monkeypatch target for `subprocess.Popen` in TUI tests:

```python
# CORRECT: module-level monkeypatch
monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: _FakePopen(*args, return_code=0, output_lines=["done"], **kwargs))

# WRONG: import-path monkeypatch
monkeypatch.setattr("erk.tui.app.subprocess.Popen", ...)  # won't work
```

This is because `app.py` uses `import subprocess` (module-level import), not `from subprocess import Popen`.

## Related Topics

- [Subprocess Testing Patterns](subprocess-testing.md) - General subprocess testing with gateway fakes
- [TUI Streaming Output](../tui/streaming-output.md) - Production streaming patterns being tested
- [Erk Test Reference](testing.md) - Comprehensive test architecture
