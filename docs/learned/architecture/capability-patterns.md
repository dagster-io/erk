---
title: Capability Implementation Patterns
read_when:
  - implementing a new capability
  - need implementation examples beyond API reference
  - choosing between capability types
tripwires:
  - action: creating a new capability without reading this doc
    warning: Load this doc first for implementation patterns and testability guidance.
---

# Capability Implementation Patterns

This document provides concrete implementation patterns for creating capabilities. For API reference and system overview, see [Capability System Architecture](capability-system.md).

## Quick Decision Tree

**Which capability type should I create?**

```
Is it a skill from .claude/skills/?
├─ Yes → Use SkillCapability base class
│        (minimal implementation: just skill_name + description)
│
└─ No → Direct Capability implementation
         │
         ├─ Does it modify ~/.claude/settings.json?
         │   └─ Yes → User-level capability (scope="user")
         │            with ClaudeInstallation gateway injection
         │
         ├─ Does it modify project settings.json?
         │   └─ Yes → Project-level capability (scope="project")
         │            that reads/writes JSON
         │
         ├─ Does it install GitHub workflows/actions?
         │   └─ Yes → See workflow-capability-pattern.md
         │
         └─ Does it create directories/files?
             └─ Yes → Standard project capability
```

## Pattern 1: SkillCapability (Minimal)

For capabilities that just install a skill directory from erk's bundled artifacts.

**When to use:** Installing `.claude/skills/<skill-name>/` from bundled artifacts.

**Implementation:** Only implement `skill_name` and `description`:

```python
# src/erk/core/capabilities/skills.py
from erk.core.capabilities.skill_capability import SkillCapability


class DignifiedPythonCapability(SkillCapability):
    """Python coding standards skill (LBYL, modern types, ABCs)."""

    @property
    def skill_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Python coding standards (LBYL, modern types, ABCs)"
```

**What the base class provides:**

- `name` = `skill_name`
- `scope` = "project"
- `installation_check_description` = ".claude/skills/{skill_name}/ directory exists"
- `artifacts` = [CapabilityArtifact for skill directory]
- `is_installed()` checks if skill directory exists
- `install()` copies skill from bundled artifacts

**Reference:** `src/erk/core/capabilities/skill_capability.py`

## Pattern 2: User-Level Capability with Gateway Injection

For capabilities that modify user-level configuration (outside any repository).

**When to use:**

- Modifying `~/.claude/settings.json`
- Modifying shell RC files (`~/.zshrc`, `~/.bashrc`)
- Any configuration outside `repo_root`

**Key characteristics:**

- `scope = "user"`
- Constructor accepts optional gateway parameters (None = use real in production)
- Gateway injection enables testing with fakes

### StatuslineCapability Example

```python
# src/erk/core/capabilities/statusline.py
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk_shared.extraction.claude_installation import (
    ClaudeInstallation,
    RealClaudeInstallation,
)


class StatuslineCapability(Capability):
    """Capability for configuring the Claude Code status line."""

    def __init__(
        self,
        *,
        claude_installation: ClaudeInstallation | None,
    ) -> None:
        """Initialize StatuslineCapability.

        Args:
            claude_installation: ClaudeInstallation for testability.
                                 If None, uses RealClaudeInstallation.
        """
        self._claude_installation = claude_installation or RealClaudeInstallation()

    @property
    def name(self) -> str:
        return "statusline"

    @property
    def scope(self) -> CapabilityScope:
        return "user"  # User-level: modifies ~/.claude/settings.json

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # settings.json is shared by multiple capabilities, so not listed
        return []

    def is_installed(self, repo_root: Path | None) -> bool:
        # User-level capability ignores repo_root
        _ = repo_root
        settings = self._claude_installation.read_settings()
        return has_erk_statusline(settings)

    def install(self, repo_root: Path | None) -> CapabilityResult:
        # User-level capability ignores repo_root
        _ = repo_root

        settings = self._claude_installation.read_settings()
        if has_erk_statusline(settings):
            return CapabilityResult(
                success=True,
                message="erk-statusline already configured",
            )

        new_settings = add_erk_statusline(settings)
        self._claude_installation.write_settings(new_settings)

        return CapabilityResult(
            success=True,
            message="Configured erk-statusline in ~/.claude/settings.json",
        )
```

**Key pattern:** `_ = repo_root` explicitly acknowledges the unused parameter for user-level capabilities.

### ShellIntegrationCapability Example (Multiple Gateways)

For complex user-level capabilities that need multiple external interactions:

```python
class ShellIntegrationCapability(Capability):
    """Capability for configuring shell integration."""

    def __init__(
        self,
        *,
        shell: Shell | None,
        console: Console | None,
        shell_integration_dir: Path | None,
    ) -> None:
        """Initialize with injectable dependencies.

        Args:
            shell: Shell gateway for detecting shell type. None = RealShell.
            console: Console gateway for user prompts. None = InteractiveConsole.
            shell_integration_dir: Path to templates. None = bundled templates.
        """
        self._shell = shell or RealShell()
        self._console = console or InteractiveConsole()
        self._shell_integration_dir = shell_integration_dir or _shell_integration_dir()
```

## Pattern 3: Settings Modification (Project-Level)

For capabilities that modify `.claude/settings.json` in a project.

**Pattern:** Read → validate → modify → write, handling shared files.

```python
class HooksCapability(Capability):
    """Capability for configuring Claude Code hooks."""

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    def is_installed(self, repo_root: Path | None) -> bool:
        if repo_root is None:
            return False
        settings_path = repo_root / ".claude" / "settings.json"
        if not settings_path.exists():
            return False
        # Check for specific hooks in settings
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        return _has_required_hooks(settings)

    def install(self, repo_root: Path | None) -> CapabilityResult:
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="HooksCapability requires repo_root",
            )

        settings_path = repo_root / ".claude" / "settings.json"

        # Read existing settings or start with empty
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return CapabilityResult(
                    success=False,
                    message="Invalid JSON in settings.json",
                )
        else:
            settings = {}
            settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if already installed (idempotency)
        if _has_required_hooks(settings):
            return CapabilityResult(
                success=True,
                message="Hooks already configured",
            )

        # Add hooks (preserving existing settings)
        settings = _add_hooks(settings)

        # Write back
        settings_path.write_text(
            json.dumps(settings, indent=2),
            encoding="utf-8",
        )

        return CapabilityResult(
            success=True,
            message="Added erk hooks to settings.json",
            created_files=(".claude/settings.json",),
        )
```

**Key patterns:**

- Handle missing file gracefully
- Handle JSON parse errors
- Preserve existing settings keys
- Idempotent: check before modifying
- Report created/modified files

## Testing Capabilities

### Testing User-Level Capabilities

Use fake gateways to avoid modifying real user files:

```python
def test_statusline_install_configures_statusline() -> None:
    """Test install configures erk-statusline in settings."""
    fake_claude = FakeClaudeInstallation.for_test(settings={})
    cap = StatuslineCapability(claude_installation=fake_claude)

    result = cap.install(None)  # User-level: repo_root is None

    assert result.success is True
    assert "Configured" in result.message

    # Verify settings were written via fake
    assert len(fake_claude.settings_writes) == 1
    written_settings = fake_claude.settings_writes[0]
    assert "statusLine" in written_settings


def test_statusline_install_idempotent() -> None:
    """Test install is idempotent when already configured."""
    fake_claude = FakeClaudeInstallation.for_test(
        settings={"statusLine": {"type": "command", "command": "uvx erk-statusline"}}
    )
    cap = StatuslineCapability(claude_installation=fake_claude)

    result = cap.install(None)

    assert result.success is True
    assert "already configured" in result.message
    # No writes should have been made
    assert len(fake_claude.settings_writes) == 0
```

### Testing Shell Integration

Use FakeShell and FakeConsole:

```python
def test_shell_integration_install_auto_modify(tmp_path: Path) -> None:
    """Test install auto-modifies RC file when user confirms."""
    rc_path = tmp_path / ".zshrc"
    rc_path.write_text("# existing content\n", encoding="utf-8")

    # Create shell integration directory with wrapper
    shell_integration_dir = tmp_path / "shell_integration"
    shell_integration_dir.mkdir()
    (shell_integration_dir / "zsh_wrapper.sh").write_text(
        "erk() { echo 'wrapper'; }\n", encoding="utf-8"
    )

    fake_shell = FakeShell(detected_shell=("zsh", rc_path))
    fake_console = FakeConsole(
        is_interactive=True,
        is_stdout_tty=True,
        is_stderr_tty=True,
        confirm_responses=[True],  # User confirms auto-modify
    )
    cap = ShellIntegrationCapability(
        shell=fake_shell,
        console=fake_console,
        shell_integration_dir=shell_integration_dir,
    )

    result = cap.install(None)

    assert result.success is True
    # Verify RC file was modified
    rc_content = rc_path.read_text(encoding="utf-8")
    assert "# Erk shell integration" in rc_content
```

### Testing Project-Level Capabilities

Use `tmp_path` fixture for filesystem:

```python
def test_hooks_install_creates_settings(tmp_path: Path) -> None:
    """Test install creates settings.json if it doesn't exist."""
    cap = HooksCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert ".claude/settings.json" in result.created_files

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
```

## Registry Registration

After creating a capability, add it to the registry:

```python
# src/erk/core/capabilities/registry.py
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        # ... existing capabilities ...
        StatuslineCapability(claude_installation=None),
        ShellIntegrationCapability(
            shell=None,
            console=None,
            shell_integration_dir=None,
        ),
    )
```

**Key pattern:** Pass `None` to gateway parameters for real implementations in production.

## Related Documentation

- [Capability System Architecture](capability-system.md) - API reference and overview
- [Bundled Artifacts System](bundled-artifacts.md) - How erk bundles and syncs artifacts
- [Workflow Capability Pattern](workflow-capability-pattern.md) - GitHub workflow capabilities
- [Gateway Inventory](gateway-inventory.md) - Available gateway interfaces for DI
