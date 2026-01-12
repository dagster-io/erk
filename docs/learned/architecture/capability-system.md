---
title: Capability System Architecture
read_when:
  - creating new erk init capabilities
  - understanding how erk init works
  - adding installable features
  - working with capability tracking in state.toml
  - understanding how erk doctor filters artifacts by installed capabilities
---

# Capability System Architecture

The capability system enables optional features to be installed via `erk init capability add <name>`.

## Core Components

### Base Class

All capabilities inherit from the `Capability` ABC in `src/erk/core/capabilities/base.py`.

**Required properties:**

| Property                         | Type                       | Purpose                                   |
| -------------------------------- | -------------------------- | ----------------------------------------- |
| `name`                           | `str`                      | CLI identifier (e.g., "tripwires-review") |
| `description`                    | `str`                      | Short description for list output         |
| `scope`                          | `CapabilityScope`          | "project" or "user"                       |
| `installation_check_description` | `str`                      | What `is_installed()` checks              |
| `artifacts`                      | `list[CapabilityArtifact]` | Files/dirs created                        |
| `managed_artifacts`              | `list[ManagedArtifact]`    | Artifacts this capability manages         |

**Required methods:**

| Method                                                   | Purpose                    |
| -------------------------------------------------------- | -------------------------- |
| `is_installed(repo_root: Path \| None) -> bool`          | Check if already installed |
| `install(repo_root: Path \| None) -> CapabilityResult`   | Install the capability     |
| `uninstall(repo_root: Path \| None) -> CapabilityResult` | Uninstall the capability   |

**Optional:**

| Property/Method        | Default | Purpose                               |
| ---------------------- | ------- | ------------------------------------- |
| `required`             | `False` | Auto-install during erk init          |
| `preflight(repo_root)` | Success | Pre-flight checks before installation |

### Registry

The registry in `src/erk/core/capabilities/registry.py` maintains a cached tuple of all capability instances.

**Query functions:**

| Function                            | Purpose                                      |
| ----------------------------------- | -------------------------------------------- |
| `get_capability(name)`              | Get capability by name                       |
| `list_capabilities()`               | All capabilities                             |
| `list_required_capabilities()`      | Only `required=True` capabilities            |
| `get_managed_artifacts()`           | All managed artifact mappings                |
| `is_capability_managed(name, type)` | Check if artifact is managed by a capability |

### Scopes

| Scope     | Description                                                | Example                                         |
| --------- | ---------------------------------------------------------- | ----------------------------------------------- |
| `project` | Requires git repository, installed relative to `repo_root` | learned-docs, dignified-python, erk-hooks       |
| `user`    | Installed anywhere, relative to home directory             | statusline (modifies `~/.claude/settings.json`) |

### Managed Artifacts

Capabilities declare which artifacts they manage using the `managed_artifacts` property. This enables the registry to serve as the single source of truth for artifact detection and health checks.

**ManagedArtifact dataclass:**

```python
@dataclass(frozen=True)
class ManagedArtifact:
    name: str                      # e.g., "dignified-python", "ruff-format-hook"
    artifact_type: ManagedArtifactType
```

**ManagedArtifactType values:**

| Type       | Description                        |
| ---------- | ---------------------------------- |
| `skill`    | Claude skills in `.claude/skills/` |
| `command`  | Claude commands                    |
| `agent`    | Claude agents                      |
| `workflow` | GitHub Actions workflows           |
| `action`   | GitHub Actions custom actions      |
| `hook`     | Claude Code hooks                  |
| `prompt`   | `.github/prompts/` files           |

**Example implementation:**

```python
class HooksCapability(Capability):
    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        return [
            ManagedArtifact(name="user-prompt-hook", artifact_type="hook"),
            ManagedArtifact(name="exit-plan-mode-hook", artifact_type="hook"),
        ]
```

**Usage:** The registry uses these declarations to answer "is this artifact erk-managed?" via `is_capability_managed(name, type)`. This replaces the previous `BUNDLED_*` frozensets in `artifact_health.py`.

## Capability Types

| Type     | Base Class        | Example                     | Installs                       |
| -------- | ----------------- | --------------------------- | ------------------------------ |
| Skill    | `SkillCapability` | `DignifiedPythonCapability` | `.claude/skills/`              |
| Workflow | `Capability`      | `DignifiedReviewCapability` | `.github/workflows/` + prompts |
| Settings | `Capability`      | `HooksCapability`           | Modifies `settings.json`       |
| Docs     | `Capability`      | `LearnedDocsCapability`     | `docs/learned/`                |

## Creating a New Capability

1. Create class in `src/erk/core/capabilities/`
2. Implement required properties and methods
3. Add to `_all_capabilities()` tuple in `registry.py`
4. Add tests in `tests/core/capabilities/`

For skill-based capabilities, extend `SkillCapability` and implement only `skill_name` and `description`. See [Bundled Artifacts](bundled-artifacts.md) for how artifacts are sourced.

For workflow capabilities that install GitHub Actions, see [Workflow Capability Pattern](workflow-capability-pattern.md).

## Capability Tracking

When capabilities are installed or uninstalled, their state is tracked in `.erk/state.toml`. This enables `erk doctor` to only check artifacts for capabilities that have been explicitly installed.

### State File Location

`.erk/state.toml` in the repository root (or worktree root for worktree-specific state).

### State File Format

```toml
[artifacts]
version = "0.5.1"
files = { ... }

[capabilities]
installed = ["dignified-python", "fake-driven-testing", "erk-impl"]
```

### Tracking API

From `erk.artifacts.state`:

| Function                                                     | Purpose                         |
| ------------------------------------------------------------ | ------------------------------- |
| `add_installed_capability(project_dir, name)`                | Record capability installation  |
| `remove_installed_capability(project_dir, name)`             | Record capability removal       |
| `load_installed_capabilities(project_dir) -> frozenset[str]` | Load installed capability names |

### Implementation Pattern

**Capability classes** should call tracking functions during `install()` and `uninstall()`:

```python
class DignifiedPythonCapability(SkillCapability):
    def install(self, repo_root: Path | None) -> CapabilityResult:
        result = super().install(repo_root)
        if result.success and repo_root:
            add_installed_capability(repo_root, self.name)
        return result

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        result = super().uninstall(repo_root)
        if result.success and repo_root:
            remove_installed_capability(repo_root, self.name)
        return result
```

### Health Check Filtering

`erk doctor` uses the installed capabilities to filter which artifacts are checked:

```python
# In health_checks.py
installed = load_installed_capabilities(project_dir)

# _get_bundled_by_type() now accepts installed_capabilities parameter
skills = _get_bundled_by_type("skill", installed_capabilities=installed)
```

**Key insight**: When `installed_capabilities=None`, all artifacts are returned (used for sync operations). When a `frozenset` is passed, only artifacts from installed capabilities are returned (used for doctor checks).

### Required vs Optional Capabilities

| Property     | Required (`required=True`) | Optional                    |
| ------------ | -------------------------- | --------------------------- |
| Auto-install | Yes, during `erk init`     | Manual via `capability add` |
| Doctor check | Always checked             | Only if installed           |
| Example      | hooks                      | dignified-python, workflows |

Required capabilities don't need tracking—they're always installed and always checked. Optional capabilities use the `[capabilities]` tracking to determine doctor check scope.

## CLI Commands

| Command                             | Purpose                   |
| ----------------------------------- | ------------------------- |
| `erk init capability list`          | Show all capabilities     |
| `erk init capability check <name>`  | Check installation status |
| `erk init capability add <name>`    | Install capability        |
| `erk init capability remove <name>` | Uninstall capability      |

## Related Topics

- [Bundled Artifacts System](bundled-artifacts.md) - How erk bundles and syncs artifacts
- [Workflow Capability Pattern](workflow-capability-pattern.md) - Pattern for GitHub workflow capabilities
