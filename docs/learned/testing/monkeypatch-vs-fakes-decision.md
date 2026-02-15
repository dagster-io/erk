---
title: Monkeypatch vs Fakes Decision Guide
read_when:
  - "choosing between monkeypatch and fakes for a test"
  - "deciding how to test code that uses Path.home()"
  - "unsure whether to create a gateway or use monkeypatch"
tripwires:
  - action: "choosing between monkeypatch and fakes for a test"
    warning: "Read monkeypatch-vs-fakes-decision.md first. Default to gateway fakes. Monkeypatch is only appropriate for process-level globals like Path.home() in exec scripts."
---

# Monkeypatch vs Fakes Decision Guide

## Default: Always Prefer Gateway Fakes

Gateway fakes are the primary test isolation mechanism in erk. They provide type-safe, stateful test doubles that track mutations for assertions.

```python
# Correct: gateway fake
fake_git = FakeGit()
fake_github = FakeGitHub()
ctx = ErkContext.for_test(git=fake_git, github=fake_github)
result = my_function(ctx)
assert fake_git.commits[0].message == "expected"
```

## Decision Tree

```
Is there a gateway for this operation?
├── YES → Use the fake gateway
│         (FakeGit, FakeGitHub, FakeGraphite, FakeClaudeInstallation, etc.)
│
└── NO → Should there be a gateway?
    ├── YES → Create the gateway first, then use its fake
    │         (See gateway-abc-implementation.md)
    │
    └── NO → Is it a process-level global?
        ├── YES → monkeypatch is acceptable
        │         (Path.home() in exec scripts, environment variables)
        │
        └── NO → Document why in the test
```

## Exception: Path.home() in Exec Scripts

Exec scripts that read from `~/.claude/` or `~/.erk/` use `Path.home()` as a process-level global. Monkeypatch is appropriate here because:

1. `Path.home()` is a stdlib function — no gateway wraps it directly
2. The ClaudeInstallation gateway handles most `~/.claude/` operations, but exec scripts sometimes need raw path access
3. Parallel test isolation requires monkeypatch to prevent reading from the real home directory

<!-- Conceptual example: illustrates the pytest monkeypatch API pattern, not copied from a specific test -->

```python
# Acceptable: monkeypatch for Path.home() in exec script test
def test_my_exec_script(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # ... test exec script that reads ~/.claude/
```

## Exception: Genuine Import Conflicts

When two modules export the same name and you need to control which one a function sees at runtime, monkeypatch on the consuming module's namespace is acceptable. This is rare.

## Anti-Patterns

| Pattern                                       | Problem                              | Fix                                |
| --------------------------------------------- | ------------------------------------ | ---------------------------------- |
| `monkeypatch.setattr(subprocess, "run", ...)` | Bypasses gateway test infrastructure | Use gateway fake                   |
| `@patch("module.function")`                   | unittest.mock is banned              | Use gateway fake                   |
| `monkeypatch.setattr(git, "method", ...)`     | Patching real gateway methods        | Use FakeGit                        |
| `monkeypatch.chdir()` in exec tests           | Doesn't inject context               | Use `ErkContext.for_test(cwd=...)` |

## Related Documentation

- [Monkeypatch Elimination Checklist](monkeypatch-elimination-checklist.md) — Migration patterns for existing monkeypatch usage
- [Exec Script Testing Patterns](exec-script-testing.md) — Path.home() alternatives for exec scripts
- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — Creating new gateways
