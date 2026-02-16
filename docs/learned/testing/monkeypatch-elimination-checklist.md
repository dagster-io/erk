---
title: Monkeypatch Elimination Checklist
read_when:
  - "migrating tests from monkeypatch to gateways"
  - "eliminating subprocess mocks or @patch decorators"
  - "encountering monkeypatch in existing tests and deciding whether to refactor"
tripwires:
  - action: "adding monkeypatch or @patch to a test"
    warning: "Use gateway fakes instead. If no gateway exists for the operation, create one first. See gateway-abc-implementation.md."
    pattern: "@patch|monkeypatch\\."
  - action: "using monkeypatch to stub Path.home() or subprocess.run()"
    warning: "These are the two most common monkeypatch targets. Both have established gateway replacements — ClaudeInstallation/ErkInstallation for paths, specific gateways for subprocess."
    pattern: "monkeypatch\\.setattr.*Path\\.home|monkeypatch.*subprocess\\.run"
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Monkeypatch Elimination Checklist

## Why Monkeypatch Is Especially Harmful in Erk

Erk's gateway ABC pattern means every external operation has a type-checked fake. Monkeypatching bypasses this entire system, creating tests that:

- **Couple to implementation, not interface** — a monkeypatch on `subprocess.run(["gh", ...])` breaks when the gateway switches from subprocess to the REST API, even though the behavior is identical
- **Evade the type checker** — patching attributes that don't exist on the ABC silently succeeds, then silently lies about coverage
- **Fragment test setup** — each test reinvents its own mock configuration instead of reusing constructor-injected fakes that are centralized and maintained

The gateway fakes already handle the hard parts (configurable success/failure, mutation tracking, assertion helpers). Monkeypatching is always duplicating work that's already done better.

## Mapping Mocked Operations to Gateways

The first migration step is identifying which gateway replaces each monkeypatch target. This mapping covers the patterns that appear most frequently in erk's test history:

| Monkeypatch Target                | Replacement Gateway                   | Why This Gateway                                         |
| --------------------------------- | ------------------------------------- | -------------------------------------------------------- |
| `subprocess.run(["gh", ...])`     | GitHub gateway (or sub-gateways)      | All `gh` CLI operations are abstracted behind GitHub ABC |
| `subprocess.run(["git", ...])`    | Git sub-gateways (`branch`, `remote`) | Git ABC is a pure facade; methods live on sub-gateways   |
| `subprocess.run(["gt", ...])`     | Graphite gateway                      | Graphite CLI wrapped identically to git                  |
| `subprocess.run(["pytest", ...])` | CIRunner gateway                      | CI check execution with structured results               |
| `Path.home()`                     | ClaudeInstallation or ErkInstallation | Path resolution abstracted to avoid filesystem coupling  |
| `time.sleep()` / `time.time()`    | Time gateway                          | Enables instant test execution for retry/wait loops      |
| `webbrowser.open()`               | Browser gateway                       | Captures URLs opened without launching a browser         |
| `os.execvp()`                     | AgentLauncher gateway                 | Process replacement abstracted with NoReturn semantics   |

If the operation doesn't map to an existing gateway, create one before migrating tests. See [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) for the 5-file (or 3-file simplified) pattern.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/ -->

Discover the current gateway list from `packages/erk-shared/src/erk_shared/gateway/` — each subdirectory with an `abc.py` is a gateway.

## Migration Decision: Refactor Production Code First

A common mistake is trying to eliminate monkeypatch from tests while leaving production code unchanged. This doesn't work because monkeypatch exists _because_ the production code hardcodes its dependencies.

**Correct order:**

1. **Refactor production code** to accept gateway ABCs as keyword-only parameters (the DI pattern)
2. **Then rewrite tests** to pass fakes instead of monkeypatching

Reversing this order leads to tests that monkeypatch the gateway injection itself — replacing one mock with another. See [Dependency Injection Patterns](../cli/dependency-injection-patterns.md) for the production-side refactoring pattern.

## Common Migration Mistakes

### Replacing monkeypatch with Mock instead of Fakes

```python
# WRONG: Replacing monkeypatch with unittest.mock — same fragility, different syntax
github = Mock(spec=GitHub)
github.merge_pr.return_value = True

# CORRECT: Use the constructor-injected fake
github = FakeGitHub(merge_pr_result=MergeResult(...))
```

`Mock(spec=...)` looks type-safe but still allows configuring return values that violate the ABC's actual contract. Fakes enforce realistic behavior because they implement the full ABC.

### Monkeypatching Path.home() Instead of Using Installation Gateways

`Path.home()` is the most tempting monkeypatch target because it appears in so many places. But the ClaudeInstallation and ErkInstallation gateways exist precisely to eliminate this — they abstract all path resolution behind an injectable interface. If production code calls `Path.home()` directly, that's a signal to inject the appropriate installation gateway instead.

### Partial Migration (Mixing monkeypatch and Fakes)

Tests that use fakes for some dependencies but monkeypatch for others are worse than fully monkeypatched tests because they create a false sense of safety. Either migrate all dependencies in a test to fakes, or leave the test as-is for a future migration.

## Verification After Migration

After completing a migration, verify these signals:

- **No `monkeypatch` fixture** in the migrated test functions
- **No `@patch` decorators** on the migrated tests
- **No `subprocess` imports** in the migrated production code
- **Type checker passes** — the ABC contract catches any mismatches between the old mock behavior and the real gateway interface
- **Explicit dependencies** — every external operation the production code needs is visible in the function signature

## Remaining Monkeypatch in Erk

Monkeypatch usage still exists in ~43 test files across the codebase, concentrated in:

- **Integration tests** (`tests/integration/`) — acceptable; these test real implementations and use monkeypatch for environment setup, not behavior mocking
- **Legacy unit tests** — migration candidates; these predate the gateway pattern
- **Health check tests** — use monkeypatch for environment variable manipulation, which has no gateway equivalent

Not all monkeypatch usage needs elimination. The targets are tests that monkeypatch _behavior_ (subprocess calls, path resolution, time). Tests that monkeypatch _environment_ (env vars, CLI arguments) are lower priority because they don't have gateway equivalents.

## Related Documentation

- [Subprocess Testing](subprocess-testing.md) — Fake-driven subprocess testing patterns
- [Gateway Inventory](../architecture/gateway-inventory.md) — Discovering available gateways
- [Dependency Injection Patterns](../cli/dependency-injection-patterns.md) — Production-side refactoring for testability
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — Creating new gateways when none exists
