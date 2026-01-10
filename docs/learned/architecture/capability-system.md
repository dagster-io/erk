---
title: Capability System Architecture
read_when:
  - "adding a new capability"
  - "modifying the capability system"
  - "understanding erk init capability commands"
---

# Capability System Architecture

The capability system provides optional features that can be installed via `erk init capability add <name>`.

## Core Components

| Component        | Location                                | Purpose                                              |
| ---------------- | --------------------------------------- | ---------------------------------------------------- |
| `Capability` ABC | `src/erk/core/capabilities/base.py`     | Abstract base class defining the capability contract |
| Registry         | `src/erk/core/capabilities/registry.py` | Hardcoded list of all capabilities                   |
| CLI Commands     | `src/erk/cli/commands/init/capability/` | add, check, list commands                            |

## Capability ABC Contract

Every capability must implement:

- `name`: CLI-facing identifier (e.g., 'learned-docs')
- `description`: Short description for help text
- `scope`: Either "project" (requires repo) or "user" (global)
- `installation_check_description`: What is_installed() checks
- `artifacts`: List of files/directories created
- `is_installed(repo_root)`: Check if already installed
- `install(repo_root)`: Install the capability

## Scope Types

- **project**: Installed per-repository, requires `repo_root` parameter
- **user**: Installed globally (e.g., ~/.claude/), `repo_root` is None

## Base Classes

- `SkillCapability`: For capabilities that install a Claude skill
- Direct `Capability` subclass: For custom capabilities

## Adding a New Capability

1. Create capability class in `src/erk/core/capabilities/`
2. Implement all abstract properties and methods
3. Add assertion `assert repo_root is not None` for project-scope caps
4. Register in `registry.py`
5. Add tests in `tests/unit/core/test_capabilities.py`

## User-Level Capability Pattern

User-level capabilities operate on global settings (e.g., ~/.claude/settings.json) rather than per-repository files.

### Key Differences from Project Capabilities

| Aspect                | Project Capability | User Capability        |
| --------------------- | ------------------ | ---------------------- |
| `scope` property      | Returns "project"  | Returns "user"         |
| `repo_root` parameter | Required (Path)    | Ignored (None)         |
| Artifacts             | Relative to repo   | Absolute paths (~/...) |
| Works outside repo    | No                 | Yes                    |

### Implementation Pattern

```python
class StatuslineCapability(Capability):
    def __init__(self, *, claude_installation: ClaudeInstallation | None) -> None:
        # Inject gateway for testability
        self._claude_installation = claude_installation or RealClaudeInstallation()

    @property
    def scope(self) -> CapabilityScope:
        return "user"

    def is_installed(self, repo_root: Path | None) -> bool:
        # Ignore repo_root for user-level capability
        _ = repo_root
        settings = self._claude_installation.read_settings()
        return has_erk_statusline(settings)
```

### Testability via Gateway Injection

User capabilities should accept their gateway (e.g., `ClaudeInstallation`) via constructor:

- **Production:** Pass `None` to use `RealClaudeInstallation`
- **Testing:** Pass `FakeClaudeInstallation` for in-memory testing

This follows the fake-driven testing pattern - see `fake-driven-testing` skill.
