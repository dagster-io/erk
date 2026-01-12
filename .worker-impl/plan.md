# Documentation Plan: Update Capability System Docs for Managed Artifacts

## Context

PR #4777 consolidated artifact management into the capabilities registry as the single source of truth. This removed the `BUNDLED_*` frozensets from `artifact_health.py` and replaced them with `managed_artifacts` property on capabilities.

### Key Changes Made
- Added `ManagedArtifact` dataclass and `ManagedArtifactType` to `base.py`
- Added `managed_artifacts` property to `Capability` ABC (default empty list)
- Each capability now declares what artifacts it manages
- Added `get_managed_artifacts()` and `is_capability_managed()` to registry
- `is_erk_managed()` now queries capability registry instead of hardcoded sets
- Added "prompt" artifact type for `.github/prompts/` files

### Files Changed
- `src/erk/core/capabilities/base.py` - New `ManagedArtifact` type and property
- `src/erk/core/capabilities/registry.py` - New registry functions
- `src/erk/artifacts/artifact_health.py` - Removed `BUNDLED_*`, added `_get_bundled_by_type()`
- All capability classes - Added `managed_artifacts` property overrides

## Raw Materials

https://gist.github.com/schrockn/bab71359b095d47c77d74217f068f633

## Documentation Items

### Item 1: Update bundled-artifacts.md

**Location:** `docs/learned/architecture/bundled-artifacts.md`
**Action:** Update
**Source:** [Impl] - Changes made in implementation

The current doc references `BUNDLED_SKILLS`, `BUNDLED_AGENTS`, etc. which no longer exist. Update to:

1. Remove the "Registry Location" section that lists `BUNDLED_*` constants
2. Add new section explaining the capability-based approach:
   - Each capability declares `managed_artifacts` property
   - Registry provides `get_managed_artifacts()` and `is_capability_managed()`
   - `_get_bundled_by_type()` helper derives sets from capabilities
3. Update the "Bundled vs Capability" table - now they're unified
4. Update any code references

### Item 2: Update capability-system.md

**Location:** `docs/learned/architecture/capability-system.md`
**Action:** Update
**Source:** [Impl] - New API added

Add documentation for the new `managed_artifacts` property:

1. Add to "Required properties" table:
   | `managed_artifacts` | `list[ManagedArtifact]` | Artifacts this capability manages |

2. Add new section "Managed Artifacts":
   - Purpose: Declares which artifacts capability manages for detection
   - The `ManagedArtifact` dataclass (name, artifact_type)
   - `ManagedArtifactType` literal values: skill, command, agent, workflow, action, hook, prompt
   - Example implementation

3. Add to "Query functions" in Registry section:
   | `get_managed_artifacts()` | All managed artifact mappings |
   | `is_capability_managed(name, type)` | Check if artifact is managed |