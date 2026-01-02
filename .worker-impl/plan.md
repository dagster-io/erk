# Plan: ErkInstallation Gateway Refactor

## Goal

Create an `ErkInstallation` gateway to replace mock-based testing of bundled path functions with fake-driven testing, following the established gateway pattern.

## Background

**Current state (master):**
- `get_bundled_claude_dir()` and `get_bundled_github_dir()` are defined in `src/erk/artifacts/sync.py` (lines 49-86)
- Both use `@cache` decorator for memoization
- Tests mock these via `unittest.mock.patch()` and `monkeypatch.setattr()` - 52+ mocking instances across 5 test files

**Problem:** Mock-based testing is fragile and inconsistent with the fake-driven testing pattern used by other gateways (`Git`, `GitHub`, `Graphite`, `Time`, etc.)

## Scope

### New Files (4)
```
packages/erk-shared/src/erk_shared/gateway/installation/
├── __init__.py          # Module exports
├── abc.py               # ErkInstallation ABC
├── real.py              # RealErkInstallation
└── fake.py              # FakeErkInstallation
```

### Files to Modify

**Core integration:**
- `packages/erk-shared/src/erk_shared/context/context.py` - Add `installation: ErkInstallation` field to ErkContext
- `packages/erk-shared/src/erk_shared/context/factories.py` - Wire RealErkInstallation in context factories
- `packages/erk-shared/src/erk_shared/context/testing.py` - Wire FakeErkInstallation in test context

**Consumers (change from module function to gateway):**
- `src/erk/artifacts/sync.py` - Use `ctx.installation` instead of calling cached functions directly
- `src/erk/artifacts/artifact_health.py` - Use `ctx.installation`
- `src/erk/artifacts/staleness.py` - Use `ctx.installation.get_current_version()`
- `src/erk/cli/commands/exec/scripts/get_prompt.py` - Use `ctx.installation`

**Test files (replace mocks with fake injection):**
1. `tests/artifacts/test_sync.py` - 23 mocking instances
2. `tests/artifacts/test_cli.py` - 10+ mocking instances
3. `tests/core/test_health_checks.py` - 14 mocking instances
4. `tests/artifacts/test_orphans.py` - 6 mocking instances
5. `tests/artifacts/test_staleness.py` - 5 mocking instances

## Interface Design

```python
# abc.py
from abc import ABC, abstractmethod
from pathlib import Path

class ErkInstallation(ABC):
    """Abstract interface for erk installation and version info."""

    @abstractmethod
    def get_bundled_claude_dir(self) -> Path:
        """Get path to bundled .claude/ directory in installed erk package."""
        ...

    @abstractmethod
    def get_bundled_github_dir(self) -> Path:
        """Get path to bundled .github/ directory in installed erk package."""
        ...

    @abstractmethod
    def get_current_version(self) -> str:
        """Get the currently installed version of erk (e.g., '0.2.1')."""
        ...
```

```python
# real.py
import importlib.metadata
from functools import cache
from pathlib import Path

from erk_shared.gateway.installation.abc import ErkInstallation

class RealErkInstallation(ErkInstallation):
    """Real implementation using package introspection."""

    def get_bundled_claude_dir(self) -> Path:
        return _get_bundled_claude_dir_cached()

    def get_bundled_github_dir(self) -> Path:
        return _get_bundled_github_dir_cached()

    def get_current_version(self) -> str:
        return importlib.metadata.version("erk")

# Module-level cached functions (moved from sync.py)
@cache
def _get_bundled_claude_dir_cached() -> Path: ...

@cache
def _get_bundled_github_dir_cached() -> Path: ...
```

```python
# fake.py
from pathlib import Path

from erk_shared.gateway.installation.abc import ErkInstallation

class FakeErkInstallation(ErkInstallation):
    """Test double with constructor-injected values."""

    def __init__(
        self,
        *,
        bundled_claude_dir: Path,
        bundled_github_dir: Path,
        current_version: str = "0.0.0-test",
    ) -> None:
        self._bundled_claude_dir = bundled_claude_dir
        self._bundled_github_dir = bundled_github_dir
        self._current_version = current_version

    def get_bundled_claude_dir(self) -> Path:
        return self._bundled_claude_dir

    def get_bundled_github_dir(self) -> Path:
        return self._bundled_github_dir

    def get_current_version(self) -> str:
        return self._current_version
```

## Implementation Steps

### Step 1: Create gateway infrastructure
Create the 4 gateway files following the established pattern:
- `abc.py` - Define `ErkInstallation` ABC
- `real.py` - Move cached logic from `sync.py`, implement `RealErkInstallation`
- `fake.py` - Implement `FakeErkInstallation` with constructor injection
- `__init__.py` - Re-export classes

### Step 2: Integrate into ErkContext
- Add `installation: ErkInstallation` field to `ErkContext` dataclass
- Update `create_minimal_context()` to use `RealErkInstallation`
- Update `context_for_test()` to accept optional `installation` parameter with `FakeErkInstallation` default

### Step 3: Update consumers to use gateway
- `sync.py` - Accept `ctx: ErkContext` parameter, use `ctx.installation`
- `artifact_health.py` - Use `ctx.installation` instead of imported functions
- `staleness.py` - Use `ctx.installation.get_current_version()` instead of importing from release_notes
- `get_prompt.py` - Use `ctx.installation`

### Step 4: Refactor test files
Replace mock patterns with fake injection for each test file:
1. `test_sync.py` - Replace `patch("erk.artifacts.sync.get_bundled_*")` with `FakeErkInstallation`
2. `test_cli.py` - Replace patches with fake injection via test context
3. `test_health_checks.py` - Replace `monkeypatch.setattr` with fake injection
4. `test_orphans.py` - Replace `monkeypatch.setattr` with fake injection
5. `test_staleness.py` - Replace patches (if version mocking included)

### Step 5: Clean up
- Remove the original `get_bundled_claude_dir()` and `get_bundled_github_dir()` from `sync.py`
- Remove `_get_erk_package_dir()` and `_is_editable_install()` helper functions from `sync.py`
- Verify no remaining mock patterns for bundled paths

## Related Documentation

**Skills to load before implementing:**
- `dignified-python` - Python coding standards
- `fake-driven-testing` - 5-layer test architecture with fakes

**Docs:**
- `docs/learned/architecture/gateway-abc-implementation.md` - Gateway checklist
- `docs/learned/testing/` - Test patterns

## Out of Scope

- `ArtifactState` persistence (stays in `state.py`)
- No dry-run wrapper needed (read-only operations)