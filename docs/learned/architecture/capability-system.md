---
title: Capability System Architecture
read_when:
  - creating new erk init capabilities
  - understanding how erk init works
  - adding installable features
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

**Required methods:**

| Method                                                 | Purpose                    |
| ------------------------------------------------------ | -------------------------- |
| `is_installed(repo_root: Path \| None) -> bool`        | Check if already installed |
| `install(repo_root: Path \| None) -> CapabilityResult` | Install the capability     |

**Optional:**

| Property/Method        | Default | Purpose                                |
| ---------------------- | ------- | -------------------------------------- |
| `required`             | `False` | Auto-install during erk init           |
| `managed_artifacts`    | `[]`    | Artifacts managed for detection/health |
| `preflight(repo_root)` | Success | Pre-flight checks before installation  |

### Registry

The registry in `src/erk/core/capabilities/registry.py` maintains a cached tuple of all capability instances.

**Query functions:**

| Function                            | Purpose                           |
| ----------------------------------- | --------------------------------- |
| `get_capability(name)`              | Get capability by name            |
| `list_capabilities()`               | All capabilities                  |
| `list_required_capabilities()`      | Only `required=True` capabilities |
| `get_managed_artifacts()`           | All managed artifact mappings     |
| `is_capability_managed(name, type)` | Check if artifact is managed      |

### Scopes

| Scope     | Description                                                | Example                                         |
| --------- | ---------------------------------------------------------- | ----------------------------------------------- |
| `project` | Requires git repository, installed relative to `repo_root` | learned-docs, dignified-python, erk-hooks       |
| `user`    | Installed anywhere, relative to home directory             | statusline (modifies `~/.claude/settings.json`) |

## Capability Types

| Type     | Base Class        | Example                     | Installs                       |
| -------- | ----------------- | --------------------------- | ------------------------------ |
| Skill    | `SkillCapability` | `DignifiedPythonCapability` | `.claude/skills/`              |
| Workflow | `Capability`      | `DignifiedReviewCapability` | `.github/workflows/` + prompts |
| Settings | `Capability`      | `HooksCapability`           | Modifies `settings.json`       |
| Docs     | `Capability`      | `LearnedDocsCapability`     | `docs/learned/`                |

## Managed Artifacts

Capabilities declare which artifacts they manage via the `managed_artifacts` property. This is the single source of truth for artifact detection and health checks.

### ManagedArtifact Type

```python
ManagedArtifactType = Literal["skill", "command", "agent", "workflow", "action", "hook", "prompt"]

@dataclass(frozen=True)
class ManagedArtifact:
    name: str  # e.g., "dignified-python", "ruff-format-hook"
    artifact_type: ManagedArtifactType
```

### Example Implementation

```python
class HooksCapability(Capability):
    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        return [
            ManagedArtifact(name="user-prompt-submit-hook", artifact_type="hook"),
            ManagedArtifact(name="exit-plan-mode-hook", artifact_type="hook"),
        ]
```

### How Detection Works

The artifact health system (`src/erk/artifacts/artifact_health.py`) uses these declarations:

1. `is_erk_managed()` queries `is_capability_managed()` for the artifact
2. Commands use prefix matching (`erk:*`) instead of capability declarations
3. `_get_bundled_by_type()` derives frozensets from capability declarations

This unifies artifact management - no more separate `BUNDLED_*` registries.

## Creating a New Capability

1. Create class in `src/erk/core/capabilities/`
2. Implement required properties and methods
3. Add to `_all_capabilities()` tuple in `registry.py`
4. Add tests in `tests/core/capabilities/`

For skill-based capabilities, extend `SkillCapability` and implement only `skill_name` and `description`. See [Bundled Artifacts](bundled-artifacts.md) for how artifacts are sourced.

For workflow capabilities that install GitHub Actions, see [Workflow Capability Pattern](workflow-capability-pattern.md).

## CLI Commands

| Command                            | Purpose                   |
| ---------------------------------- | ------------------------- |
| `erk init capability list`         | Show all capabilities     |
| `erk init capability check <name>` | Check installation status |
| `erk init capability add <name>`   | Install capability        |

## Related Topics

- [Bundled Artifacts System](bundled-artifacts.md) - How erk bundles and syncs artifacts
- [Workflow Capability Pattern](workflow-capability-pattern.md) - Pattern for GitHub workflow capabilities
