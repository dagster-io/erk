# Documentation Plan: Capability Tracking System [erk-learn]

## Context

Plan #4817 added capability tracking to `.erk/state.toml` so that `erk doctor` only checks artifacts for capabilities that have been explicitly installed in a repo.

### Key Files Added/Modified

- `src/erk/artifacts/state.py` - NEW functions for capability tracking
- `src/erk/artifacts/artifact_health.py` - Modified `_get_bundled_by_type()` with filtering
- `src/erk/core/health_checks.py` - Loads installed capabilities for doctor checks
- `src/erk/core/capabilities/*.py` - Install/uninstall methods now track state

### How Capability Tracking Works

When a capability is installed via `erk capability add <name>`:
1. The capability's `install()` method is called
2. The method calls `add_installed_capability(project_dir, capability_name)` 
3. This writes to `.erk/state.toml` under `[capabilities]` section

When `erk doctor` runs:
1. `load_installed_capabilities(project_dir)` reads from state.toml
2. `_get_bundled_by_type()` filters artifacts by installed capabilities
3. Only installed optional capabilities are checked; required capabilities (hooks) are always checked

### New API Functions (state.py)

```python
def add_installed_capability(project_dir: Path, capability_name: str) -> None:
    """Record a capability as installed in .erk/state.toml."""

def remove_installed_capability(project_dir: Path, capability_name: str) -> None:
    """Remove a capability from installed tracking."""

def load_installed_capabilities(project_dir: Path) -> frozenset[str]:
    """Load set of installed capability names from state.toml."""
```

### Important Pattern: installed_capabilities Parameter

The `_get_bundled_by_type()` function now takes an `installed_capabilities` parameter:

```python
# Check ALL artifacts (for sync, orphan detection, missing detection)
_get_bundled_by_type("skill", installed_capabilities=None)

# Check only installed artifacts (for erk doctor health checks)
_get_bundled_by_type("skill", installed_capabilities=frozenset({"dignified-python"}))
```

**When to use None**: Sync operations, orphan detection, missing artifact detection - these need to see all artifacts.

**When to filter**: `erk doctor` health checks - should only report on capabilities the user has installed.

## Raw Materials

https://gist.github.com/schrockn/888088f4e0f82cd755c335d2798edd69

## Documentation Items

### 1. Add Capability Tracking to Glossary

**Location**: `docs/learned/glossary.md`
**Action**: Update - add new glossary entries

**Draft content**:

```markdown
### Capability

A feature or functionality that can be installed into a repository managed by erk. Capabilities control which artifacts (skills, workflows, agents, actions) are installed and tracked.

**Types**:
- **Required capabilities** (`required=True`): Always checked by `erk doctor` (e.g., hooks)
- **Optional capabilities**: Only checked if explicitly installed (e.g., skills, workflows)

**Management**:
```bash
erk capability add <name>    # Install a capability
erk capability remove <name> # Uninstall a capability
erk capability list          # Show installed capabilities
```

**Tracking**: Installed capabilities are recorded in `.erk/state.toml` under `[capabilities]`.

### Installed Capabilities

The set of capabilities explicitly installed in a repository, tracked in `.erk/state.toml`.

**Location**: `.erk/state.toml` under `[capabilities]` section

**Format**:
```toml
[capabilities]
installed = ["dignified-python", "erk-impl"]
```

**API** (in `erk.artifacts.state`):
- `add_installed_capability(project_dir, name)` - Record installation
- `remove_installed_capability(project_dir, name)` - Record removal
- `load_installed_capabilities(project_dir)` - Load installed set

**Usage**: `erk doctor` uses this to only check artifacts for installed capabilities.
```

### 2. Document state.toml Structure

**Location**: `docs/learned/architecture/` (new file or update existing)
**Action**: Create or update architecture doc

**Draft content** (for new section or file):

```markdown
## .erk/state.toml

Repository-local state file tracking erk's runtime state.

### Location

`.erk/state.toml` in the repo root (or worktree root for worktree-specific state).

### Sections

#### [artifacts]

Tracks artifact installation state:
```toml
[artifacts]
version = "0.5.1"
files = { ... }
```

#### [capabilities]

Tracks which capabilities are installed:
```toml
[capabilities]
installed = ["dignified-python", "fake-driven-testing", "erk-impl"]
```

### API Functions

From `erk.artifacts.state`:

- `load_artifact_state(project_dir)` - Load artifact state
- `save_artifact_state(project_dir, state)` - Save artifact state  
- `load_installed_capabilities(project_dir)` - Load installed capability names
- `add_installed_capability(project_dir, name)` - Record capability installation
- `remove_installed_capability(project_dir, name)` - Record capability removal

### When to Use

**Capability classes** should call `add_installed_capability()` during `install()` and `remove_installed_capability()` during `uninstall()`.

**Health checks** should call `load_installed_capabilities()` to filter which artifacts to check.
```

## Source Attribution

- **[Plan]** Planning session discovered the capability system structure and filtering need
- **[Impl]** Implementation session added the tracking functions and integrated filtering