---
title: Adding Workflow Capabilities
read_when:
  - "adding workflow capabilities"
  - "creating GitHub Actions workflow capabilities"
  - "understanding workflow capability pattern"
last_audited: "2026-02-16 08:00 PT"
audit_result: clean
tripwires:
  - action: "implementing workflow capabilities"
    warning: "Workflow capabilities extend Capability directly, not a template base class"
  - action: "installing workflow artifacts"
    warning: "Workflows must exist in bundled artifacts path resolved by get_bundled_github_dir()"
  - action: "importing artifacts.state in workflow capabilities"
    warning: "Use inline imports for artifacts.state to avoid circular dependencies"
---

# Adding Workflow Capabilities

## Why Workflows Are Different

Unlike skills, commands, and reviews which share common installation patterns (copy file, register name), workflow capabilities require unique installation logic:

- **Single-file workflows** copy one YAML file (e.g., `learn.yml`)
- **Multi-artifact workflows** copy workflows plus custom actions (e.g., `plan-implement.yml` + 2 action directories)
- **Dependency checks** may be needed before installation (e.g., verifying GitHub CLI is configured)
- **Validation logic** varies by workflow (e.g., checking required secrets are set)

A template base class would need parameters for all these variations, creating more complexity than implementing `Capability` directly.

## The Capability ABC Contract

<!-- Source: src/erk/core/capabilities/base.py, Capability -->

All workflow capabilities implement the `Capability` ABC from `src/erk/core/capabilities/base.py`. The contract requires:

**Identity properties:**

- `name` — CLI identifier (e.g., `"learn-workflow"`)
- `description` — Short description for help text
- `scope` — Always `"project"` for workflows (they install into `.github/`)
- `installation_check_description` — What `is_installed()` checks (e.g., `".github/workflows/learn.yml exists"`)

**Artifact tracking:**

- `artifacts` — List of `CapabilityArtifact` describing installed files/directories
- `managed_artifacts` — List of `ManagedArtifact` linking to artifact detection system

**Installation lifecycle:**

- `is_installed()` — Check if workflow files exist
- `install()` — Copy from bundled artifacts, record installation
- `uninstall()` — Remove workflow files, clear installation record

## Two Installation Patterns

### Single-File Pattern

<!-- Source: src/erk/capabilities/workflows/learn.py, LearnWorkflowCapability -->

For workflows that install one YAML file, see `LearnWorkflowCapability` in `src/erk/capabilities/workflows/learn.py`:

1. Copy workflow YAML from bundled artifacts to `.github/workflows/`
2. Call `add_installed_capability()` to record installation
3. Return success/failure result

The key insight: **bundled artifacts path differs between editable and wheel installs**. Use `get_bundled_github_dir()` to abstract this — it returns the repo root `.github/` for editable installs, `erk/data/github/` for wheel installs.

### Multi-Artifact Pattern

<!-- Source: src/erk/capabilities/workflows/erk_impl.py, ErkImplWorkflowCapability -->

For workflows that install multiple files (workflow + custom actions), see `ErkImplWorkflowCapability` in `src/erk/capabilities/workflows/erk_impl.py`:

1. Copy workflow YAML to `.github/workflows/`
2. Copy action directories to `.github/actions/` using recursive copy helper
3. Track count of installed artifacts in success message
4. Record single capability installation (not per-artifact)

**Why recursive copy helper?** Custom actions contain multiple files (`action.yml` + scripts). The `_copy_directory()` helper preserves directory structure using `rglob("*")` to walk the source tree.

## Circular Dependency Avoidance

**Critical:** Workflow capabilities use inline imports for `artifacts.state` functions:

```python
def install(self, repo_root: Path | None) -> CapabilityResult:
    # Inline import: avoids circular dependency with artifacts module
    from erk.artifacts.state import add_installed_capability
    from erk.artifacts.sync import get_bundled_github_dir
```

**Why inline?** The `artifacts` module imports from `core.capabilities` to use capability types. Top-level imports from capabilities back to artifacts create a cycle. Inline imports defer the cycle until method execution, when both modules are already loaded.

This is the **only** acceptable use of inline imports in erk. Avoid them everywhere else.

## Registry Integration

<!-- Source: src/erk/core/capabilities/registry.py, _all_capabilities -->

After creating the capability class:

1. Add import to `src/erk/core/capabilities/registry.py`
2. Add instance to `_all_capabilities()` tuple

The registry is a cached singleton. Adding to the tuple makes the capability visible to `erk init capability list` and `erk init capability add`.

**Order doesn't matter** — the registry sorts by name when listing.

## Bundled Artifact Path Resolution

<!-- Source: src/erk/artifacts/paths.py, get_bundled_github_dir -->

Workflow YAML files must exist in the bundled artifacts directory:

**Editable installs:** Place files at `.github/workflows/<name>.yml` in the erk repo
**Wheel installs:** `pyproject.toml` force-includes `.github/` to `erk/data/github/`

Use `get_bundled_github_dir()` from `src/erk/artifacts/paths.py` to get the correct path for the current install type. Never hardcode paths.

## Managed Artifacts Declaration

The `managed_artifacts` property links capability installation to artifact detection:

**Single-file workflow:**

```python
@property
def managed_artifacts(self) -> list[ManagedArtifact]:
    return [ManagedArtifact(name="learn", artifact_type="workflow")]
```

**Multi-artifact workflow:**

```python
@property
def managed_artifacts(self) -> list[ManagedArtifact]:
    return [
        ManagedArtifact(name="plan-implement", artifact_type="workflow"),
        ManagedArtifact(name="setup-claude-code", artifact_type="action"),
        ManagedArtifact(name="setup-claude-erk", artifact_type="action"),
    ]
```

**Why this matters:** The registry's `get_managed_artifacts()` builds a map of (name, type) → capability. Other systems use this to distinguish erk-managed artifacts from project-specific ones.

## Installation State Tracking

<!-- Source: erk/artifacts/state.py, add_installed_capability / remove_installed_capability -->

Workflow installations are tracked in `.erk/state/installed-capabilities.txt`:

- `add_installed_capability(repo_root, name)` appends the capability name
- `remove_installed_capability(repo_root, name)` removes the line

This state file is **single source of truth** for "is this capability installed?" It persists across uninstallation (unlike checking file existence, which fails if users manually delete files).

**Uninstall must clear state even if files are missing** — otherwise re-installation attempts will skip installation due to stale state.

## Testing Workflow Capabilities

Use CLI commands to verify registration and installation:

```bash
# Verify capability appears in registry
erk init capability list

# Check installation status
erk init capability list <name>

# Install
erk init capability add <name>

# Remove
erk init capability remove <name>
```

**Don't write unit tests for workflow capabilities.** The installation logic is trivial (copy files, record state). Testing would require mocking the filesystem and bundled artifacts path, which adds maintenance burden for little value.

Integration testing via CLI commands catches the real failure modes: missing bundled artifacts, wrong paths, circular imports.

## Decision: When to Add vs Modify

**Add a new workflow capability when:**

- Creating a new GitHub Actions workflow
- The workflow has unique installation requirements (multi-file, dependencies, etc.)

**Modify existing workflow capability when:**

- Updating the workflow YAML content
- Adding/removing custom actions from an existing workflow
- Changing installation validation logic

**Never create a workflow capability for project-specific workflows** — those should be committed directly to `.github/workflows/` in the target repo, not distributed via erk capabilities.

## Related Documentation

- [Adding New Capabilities](adding-new-capabilities.md) — General capability pattern
- [Folder Structure](folder-structure.md) — Where capability files go
