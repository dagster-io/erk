---
title: Capability System Architecture
read_when:
  - "creating new erk init capabilities"
  - "understanding how erk init works"
  - "adding installable features"
  - "working with capability tracking in state.toml"
  - "understanding how erk doctor filters artifacts by installed capabilities"
  - "working with backend-aware capability filtering"
last_audited: "2026-02-17 00:00 PT"
audit_result: edited
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

<!-- Source: src/erk/core/capabilities/registry.py, _all_capabilities -->

Factory functions can batch-register capabilities using tuple unpacking in `_all_capabilities()`. See `_all_capabilities()` in `src/erk/core/capabilities/registry.py` for the full declaration. The `*` operator unpacks a list of capabilities into the tuple, keeping the registry declaration clean while allowing factory functions to produce multiple capabilities. See [Bundled Skill Capabilities](../capabilities/bundled-skills.md) for the full pattern.

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

## Backend Awareness

Capabilities declare which agent backends they support. This enables filtering capabilities by the user's configured backend.

### supported_backends Property

<!-- Source: src/erk/core/capabilities/base.py, Capability.supported_backends -->

See `Capability.supported_backends` property in `src/erk/core/capabilities/base.py`. Returns a tuple of `AgentBackend` values (default: both `"claude"` and `"codex"`).

`AgentBackend = Literal["claude", "codex"]` (defined in `packages/erk-shared/src/erk_shared/context/types.py`).

Override this property in capability subclasses to restrict to specific backends. The default supports both.

### Backend-Specific Filtering

<!-- Source: src/erk/core/capabilities/registry.py, list_capabilities_for_backend -->

**Registry function:** `list_capabilities_for_backend()` in `src/erk/core/capabilities/registry.py`. Filters `_all_capabilities()` to those supporting the given backend, sorted by name.

**CLI filtering** in `capability add` (`src/erk/cli/commands/init/capability/add_cmd.py`): Capabilities that don't support the current backend are skipped with a warning message.

### Backend Resolution

<!-- Source: src/erk/cli/commands/init/capability/backend_utils.py, resolve_backend -->

See `resolve_backend()` in `src/erk/cli/commands/init/capability/backend_utils.py`. Reads the backend from `ctx.global_config.interactive_agent.backend`, defaulting to `"claude"`.

The backend is determined from the user's global config (`~/.config/erk/config.toml`), defaulting to `"claude"`.

### Config Migration: [interactive-claude] -> [interactive-agent]

**Location:** `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py` (line 62)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py, ia_data cascading fallback -->

The config reader uses cascading fallback. See the `ia_data` assignment in `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`.

- **Reading**: Checks `[interactive-agent]` first, falls back to `[interactive-claude]`
- **Writing**: Always writes `[interactive-agent]` (new section name)
- **Field migration**: `sandbox_mode` -> `permission_mode` (with fallback)

## Related Topics

- [Bundled Artifacts System](bundled-artifacts.md) - How erk bundles and syncs artifacts
- [Workflow Capability Pattern](workflow-capability-pattern.md) - Pattern for GitHub workflow capabilities
- [Hook Marker Detection](hook-marker-detection.md) - Version-aware detection for hooks
