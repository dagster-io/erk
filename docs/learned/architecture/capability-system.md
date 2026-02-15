---
title: Capability System Architecture
read_when:
  - creating new erk init capabilities
  - understanding how erk init works
  - adding installable features
  - working with capability tracking in state.toml
  - understanding how erk doctor filters artifacts by installed capabilities
last_audited: "2026-02-05 12:52 PT"
audit_result: clean
---

# Capability System Architecture

The capability system enables optional features to be installed via `erk init capability add <name>`.

## Core Components

### Base Class

All capabilities inherit from the `Capability` ABC in `src/erk/core/capabilities/base.py`.

See the base class for the complete interface including:

- Required properties: `name`, `description`, `scope`, `installation_check_description`, `artifacts`, `managed_artifacts`
- Required methods: `is_installed()`, `install()`, `uninstall()`
- Optional: `required` property (default `False`), `preflight()` method

### Registry

The registry in `src/erk/core/capabilities/registry.py` maintains a cached tuple of all capability instances.

**Key functions:** `get_capability(name)`, `list_capabilities()`, `list_required_capabilities()`, `get_managed_artifacts()`, `is_capability_managed(name, type)`

#### Registry Splice Pattern

Factory functions can batch-register capabilities using tuple unpacking in `_all_capabilities()`:

```python
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        LearnedDocsCapability(),
        *create_bundled_skill_capabilities(),  # unpacks list into tuple
        TripwiresReviewDefCapability(),
        # ...
    )
```

The `*` operator unpacks a list of capabilities into the tuple, keeping the registry declaration clean while allowing factory functions to produce multiple capabilities. See [Bundled Skill Capabilities](../capabilities/bundled-skills.md) for the full pattern.

### Scopes

| Scope     | Description                                                | Example                                         |
| --------- | ---------------------------------------------------------- | ----------------------------------------------- |
| `project` | Requires git repository, installed relative to `repo_root` | learned-docs, dignified-python, erk-hooks       |
| `user`    | Installed anywhere, relative to home directory             | statusline (modifies `~/.claude/settings.json`) |

### Managed Artifacts

Capabilities declare which artifacts they manage using the `managed_artifacts` property. This enables the registry to serve as the single source of truth for artifact detection and health checks.

See `ManagedArtifact` dataclass and `ManagedArtifactType` in `src/erk/core/capabilities/base.py` for the complete type definitions.

## Capability Types

| Type     | Base Class        | Example                     | Installs                       |
| -------- | ----------------- | --------------------------- | ------------------------------ |
| Skill    | `SkillCapability` | `DignifiedPythonCapability` | `.claude/skills/`              |
| Workflow | `Capability`      | `DignifiedReviewCapability` | `.github/workflows/` + prompts |
| Settings | `Capability`      | `HooksCapability`           | Modifies `settings.json`       |
| Docs     | `Capability`      | `LearnedDocsCapability`     | `docs/learned/`                |

## Creating a New Capability

1. Create class in `src/erk/core/capabilities/`
2. Implement required properties and methods (see `Capability` ABC)
3. Add to `_all_capabilities()` tuple in `registry.py`
4. Add tests in `tests/core/capabilities/`

For skill-based capabilities, extend `SkillCapability` and implement only `skill_name` and `description`. See [Bundled Artifacts](bundled-artifacts.md) for how artifacts are sourced.

For workflow capabilities that install GitHub Actions, see [Workflow Capability Pattern](workflow-capability-pattern.md).

## Capability Tracking

When capabilities are installed or uninstalled, their state is tracked in `.erk/state.toml`. This enables `erk doctor` to only check artifacts for capabilities that have been explicitly installed.

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

- `add_installed_capability(project_dir, name)` — Record capability installation
- `remove_installed_capability(project_dir, name)` — Record capability removal
- `load_installed_capabilities(project_dir) -> frozenset[str]` — Load installed capability names

### Implementation Pattern

Capability classes should call tracking functions during `install()` and `uninstall()`. See existing implementations like `DignifiedPythonCapability` for the pattern.

### Health Check Filtering

`erk doctor` uses installed capabilities to filter which artifacts are checked:

- When `installed_capabilities=None`: All artifacts returned (used within erk repo itself)
- When `frozenset` passed: Only artifacts from installed capabilities (consumer repos)

### Required vs Optional Capabilities

| Property     | Required (`required=True`) | Optional                    |
| ------------ | -------------------------- | --------------------------- |
| Auto-install | Yes, during `erk init`     | Manual via `capability add` |
| Doctor check | Always checked             | Only if installed           |
| Example      | hooks                      | dignified-python, workflows |

Required capabilities don't need tracking—they're always installed and always checked.

## CLI Commands

| Command                             | Purpose                                                    |
| ----------------------------------- | ---------------------------------------------------------- |
| `erk init capability list [name]`   | Show all capabilities with status, or detailed view of one |
| `erk init capability add <name>`    | Install capability                                         |
| `erk init capability remove <name>` | Uninstall capability                                       |

## Related Topics

- [Bundled Artifacts System](bundled-artifacts.md) - How erk bundles and syncs artifacts
- [Workflow Capability Pattern](workflow-capability-pattern.md) - Pattern for GitHub workflow capabilities
- [Hook Marker Detection](hook-marker-detection.md) - Version-aware detection for hooks
