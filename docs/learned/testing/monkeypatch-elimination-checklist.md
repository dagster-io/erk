---
title: Monkeypatch Elimination Checklist
read_when:
  - "migrating tests from monkeypatch to gateways"
  - "eliminating subprocess mocks"
  - "refactoring tests to use fakes"
---

# Monkeypatch Elimination Checklist

A step-by-step checklist for migrating tests from monkeypatch/subprocess mocks to the gateway fake pattern.

## Why Eliminate Monkeypatch?

**Problem with monkeypatch:**

- Brittle - Breaks when implementation details change
- Unclear - Hidden coupling to internal structure
- Hard to maintain - Scattered across test files
- No type safety - Mocking attributes that don't exist

**Benefits of gateway fakes:**

- Robust - Interface changes caught by type checker
- Clear - Explicit dependencies in function signatures
- Maintainable - Fakes are centralized and reusable
- Type-safe - ABC contract enforced

## Migration Checklist

### Step 1: Identify Monkeypatch Usage

Find tests using monkeypatch:

```bash
grep -r "monkeypatch" tests/
grep -r "subprocess.run" tests/
grep -r "@patch" tests/
```

Common patterns to look for:

- `monkeypatch.setattr(subprocess, "run", ...)`
- `monkeypatch.setattr(Path, "home", ...)`
- `@patch("subprocess.run")`
- `mock.Mock(return_value=...)`

### Step 2: Identify the Capability Being Mocked

What external operation is being simulated?

| Mocked Operation | Gateway to Use |
|------------------|----------------|
| `subprocess.run(["gh", ...])` | GitHub gateway |
| `subprocess.run(["git", ...])` | Git gateway |
| `subprocess.run(["pytest", ...])` | CIRunner gateway |
| `Path.home()` | ClaudeInstallation or ErkInstallation |
| `time.sleep()` | Time gateway |
| `webbrowser.open()` | Browser gateway |

### Step 3: Check If Gateway Exists

Look in gateway inventory:

- [Gateway Inventory](../architecture/gateway-inventory.md)
- `packages/erk-shared/src/erk_shared/gateway/`

If the gateway doesn't exist, you may need to create it first. See [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md).

### Step 4: Refactor Production Code

#### Before: Direct subprocess/Path usage

```python
def my_command() -> None:
    result = subprocess.run(["gh", "pr", "list"])
    if result.returncode == 0:
        print("Success")
```

#### After: Gateway injection

```python
def my_command(*, github: GitHub) -> None:
    prs = github.list_prs(repo_root=Path.cwd())
    if prs:
        print("Success")
```

### Step 5: Update Entry Point

#### Before: No dependencies

```python
def main() -> int:
    my_command()
    return 0
```

#### After: Create real gateways

```python
def main() -> int:
    from erk_shared.gateway.github.real import RealGitHub

    my_command(github=RealGitHub())
    return 0
```

### Step 6: Refactor Tests

#### Before: Monkeypatch

```python
def test_my_command(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    my_command()
    # No clear assertion about what was called
```

#### After: Gateway fake

```python
def test_my_command():
    from erk_shared.gateway.github.fake import FakeGitHub

    fake_github = FakeGitHub(prs=[...])

    my_command(github=fake_github)

    # Clear assertion using fake's tracking
    assert len(fake_github.list_prs_calls) == 1
```

### Step 7: Remove Monkeypatch Imports

After migration, remove:

```python
# Remove these
import subprocess
from unittest.mock import Mock, patch
# Potentially remove (if no longer used)
pytest.MonkeyPatch from test signatures
```

### Step 8: Verify Tests Pass

Run the test suite:

```bash
pytest tests/test_my_command.py -v
```

Verify:

- ✅ Tests pass
- ✅ No subprocess calls during tests
- ✅ No monkeypatch usage
- ✅ Type checker passes

## Common Migration Patterns

### Pattern 1: subprocess.run → Gateway

**Before:**

```python
def test_command(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    my_command()

    assert calls == [["pytest"]]
```

**After:**

```python
def test_command():
    fake_ci = FakeCIRunner.create_passing_all()

    my_command(ci_runner=fake_ci)

    assert fake_ci.check_names_run == ["pytest"]
```

### Pattern 2: Path.home() → Installation Gateway

**Before:**

```python
def test_command(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    result = get_config()

    assert result.config_dir == fake_home / ".erk"
```

**After:**

```python
def test_command(tmp_path):
    from erk_shared.gateway.erk_installation.fake import FakeErkInstallation

    fake_erk = FakeErkInstallation(root=tmp_path / ".erk")

    result = get_config(erk=fake_erk)

    assert result.config_dir == tmp_path / ".erk"
```

### Pattern 3: Configuring Fake Behavior

Fakes use constructor injection to configure behavior:

```python
# Success case
fake_ci = FakeCIRunner.create_passing_all()

# Specific failures
fake_ci = FakeCIRunner(
    failing_checks={"ruff", "pytest"},
    missing_commands={"prettier"},
)

# Sequential responses
fake_executor = FakePromptExecutor(
    outputs=["First response", "Second response"]
)
```

## Verification

After migration, verify:

- [ ] No `monkeypatch` in test files
- [ ] No `subprocess.run` in production code
- [ ] No `@patch` decorators
- [ ] All tests pass
- [ ] Type checker passes
- [ ] Production code has explicit gateway dependencies
- [ ] Tests use gateway fakes for behavior simulation

## Related Documentation

- [Subprocess Testing](subprocess-testing.md) - Fake-driven subprocess testing
- [Gateway Inventory](../architecture/gateway-inventory.md) - Available gateways
- [Dependency Injection Patterns](../cli/dependency-injection-patterns.md) - Injecting gateways in exec scripts
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - Creating new gateways
