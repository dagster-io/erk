---
title: Monkeypatch Elimination Checklist
read_when:
  - "migrating tests from monkeypatch to gateways"
  - "eliminating subprocess mocks"
  - "refactoring tests to use fakes"
last_audited: "2026-02-05"
audit_result: edited
---

# Monkeypatch Elimination Checklist

A step-by-step checklist for migrating tests from monkeypatch/subprocess mocks to the gateway fake pattern.

## Why Eliminate Monkeypatch?

| Aspect          | monkeypatch                               | Gateway fakes                                |
| --------------- | ----------------------------------------- | -------------------------------------------- |
| Brittleness     | Breaks when implementation details change | Interface changes caught by type checker     |
| Clarity         | Hidden coupling to internal structure     | Explicit dependencies in function signatures |
| Maintainability | Scattered across test files               | Centralized and reusable fakes               |
| Type safety     | Mocking attributes that may not exist     | ABC contract enforced                        |

## Migration Checklist

### Step 1: Identify Monkeypatch Usage

Find tests using monkeypatch patterns:

```bash
grep -r "monkeypatch" tests/
grep -r "subprocess.run" tests/
grep -r "@patch" tests/
```

### Step 2: Map Mocked Operation to Gateway

| Mocked Operation                  | Gateway to Use                        |
| --------------------------------- | ------------------------------------- |
| `subprocess.run(["gh", ...])`     | GitHub gateway                        |
| `subprocess.run(["git", ...])`    | Git gateway                           |
| `subprocess.run(["pytest", ...])` | CIRunner gateway                      |
| `Path.home()`                     | ClaudeInstallation or ErkInstallation |
| `time.sleep()`                    | Time gateway                          |
| `webbrowser.open()`               | Browser gateway                       |

If the gateway doesn't exist, create it first. See [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md).

### Step 3: Refactor Production Code

Replace direct subprocess/Path usage with gateway injection — accept ABC types as keyword-only parameters. See [Dependency Injection Patterns](../cli/dependency-injection-patterns.md) for the full pattern.

### Step 4: Refactor Tests

Replace monkeypatch with gateway fakes. Fakes live in `packages/erk-shared/src/erk_shared/gateway/*/fake.py`. Each fake accepts constructor parameters to configure behavior (success/failure scenarios, preconfigured data).

### Step 5: Verify

After migration:

- No `monkeypatch` in test files
- No `subprocess.run` in production code
- No `@patch` decorators
- All tests pass
- Type checker passes
- Production code has explicit gateway dependencies

## Related Documentation

- [Subprocess Testing](subprocess-testing.md) — Fake-driven subprocess testing
- [Gateway Inventory](../architecture/gateway-inventory.md) — Available gateways
- [Dependency Injection Patterns](../cli/dependency-injection-patterns.md) — Injecting gateways in exec scripts
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — Creating new gateways
