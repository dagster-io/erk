# Extraction Plan: Capability System Scope Documentation

## Objective

Add documentation for the capability system scope feature, covering both the architectural patterns and implementation guidance.

## Source Information

- **Implementation Session:** ca168296-de62-400b-a838-d409e95fba0b
- **Related PR:** #4526 (Add Scope to Capability System)

---

## Documentation Items

### Item 1: Capability System Architecture (Category A - Learning Gap)

**Location:** `docs/learned/architecture/capability-system.md` (new file)
**Priority:** Medium
**Action:** Create

**Content:**

```markdown
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
```

---

### Item 2: User-Level Capability Pattern (Category B - Teaching Gap)

**Location:** `docs/learned/architecture/capability-system.md` (append to Item 1)
**Priority:** High
**Action:** Append

**Content:**

````markdown
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
````

### Testability via Gateway Injection

User capabilities should accept their gateway (e.g., `ClaudeInstallation`) via constructor:

- **Production:** Pass `None` to use `RealClaudeInstallation`
- **Testing:** Pass `FakeClaudeInstallation` for in-memory testing

This follows the fake-driven testing pattern - see `fake-driven-testing` skill.

````

---

### Item 3: ClaudeInstallation Gateway (Category A - Learning Gap)

**Location:** `docs/learned/architecture/gateway-abc-implementation.md` (update)
**Priority:** Medium
**Action:** Update (add to gateway list)

**Content:**

Add to the gateway list in the existing document:

```markdown
### ClaudeInstallation

**Location:** `packages/erk-shared/src/erk_shared/extraction/claude_installation/`

| Implementation | Purpose |
|----------------|---------|
| `ClaudeInstallation` (ABC) | Abstract interface for Claude Code settings/sessions |
| `RealClaudeInstallation` | Production - reads from ~/.claude/ |
| `FakeClaudeInstallation` | Testing - in-memory with configurable state |

**Key methods:**
- `read_settings()`: Read ~/.claude/settings.json
- `write_settings(settings)`: Write settings with backup
- `settings_exists()`: Check if settings file exists

**Test usage:**
```python
fake_claude = FakeClaudeInstallation.for_test(
    settings={"statusLine": {"type": "command", "command": "uvx erk-statusline"}}
)
cap = StatuslineCapability(claude_installation=fake_claude)
````

````

---

### Item 4: Capability CLI Scope Handling (Category B - Teaching Gap)

**Location:** `docs/learned/cli/capability-commands.md` (new file)
**Priority:** Low
**Action:** Create

**Content:**

```markdown
---
title: Capability CLI Commands
read_when:
  - "using erk init capability commands"
  - "troubleshooting capability installation"
---

# Capability CLI Commands

## Commands

### `erk init capability list`

Lists all capabilities with scope labels:

````

Available capabilities:
learned-docs [project] Autolearning documentation system
statusline [user] Claude Code status line configuration

```

### `erk init capability add <name>`

Installs capability. Behavior depends on scope:

- **project** capabilities: Require being in a git repository
- **user** capabilities: Work from anywhere

### `erk init capability check [name]`

Without name: Shows all capabilities with status
- Project caps show "?" when outside git repo
- User caps always show installed/not-installed status

With name: Shows detailed status for that capability
- Project caps fail with error if outside git repo
- User caps work from anywhere
```

---

## Verification

After implementing, run:

- `erk docs sync` to regenerate index files
- `erk docs validate` to check frontmatter
