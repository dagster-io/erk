---
title: Kit Install Architecture
read_when:
  - modifying kit install/update logic
  - debugging kit installation
  - understanding kit resolution
tripwires:
  - action: "modifying kit install/update logic"
    warning: "Understand the idempotent design and atomic hook updates. The install command handles both fresh installs and updates with rollback on failure."
---

# Kit Install Architecture

Internal architecture documentation for the consolidated `erk kit install` command.

## Idempotent Design

The install command is fully idempotent:

- **Kit not installed** → Fresh install workflow
- **Kit installed, version differs** → Update workflow (sync)
- **Kit installed, version matches** → No-op (reports "already up to date")
- **Kit installed + `--force`** → Reinstall regardless of version

This eliminates the need for separate `install` vs `update` vs `sync` commands.

## Data Structures

### UpdateCheckResult

```python
class UpdateCheckResult(NamedTuple):
    has_update: bool           # True if update available (or force=True)
    resolved: ResolvedKit | None  # Resolved kit info, None on error
    error_message: str | None  # Error description if resolution failed
```

Resolution errors are captured in `error_message` rather than returning "up to date" to prevent silent failures.

### SyncResult

```python
@dataclass(frozen=True)
class SyncResult:
    kit_id: str
    old_version: str
    new_version: str
    was_updated: bool
    artifacts_updated: int
    updated_kit: InstalledKit | None
```

### ResolvedKit

```python
@dataclass(frozen=True)
class ResolvedKit:
    kit_id: str           # Globally unique identifier
    source_type: SourceType
    version: str
    manifest_path: Path
    artifacts_base: Path
```

## Workflow Routing

```
install(kit_id)
    │
    ├── kit_id in config.kits?
    │       │
    │       ├── Yes → _handle_update_workflow()
    │       │           │
    │       │           ├── check_for_updates()
    │       │           ├── sync_kit()
    │       │           └── _process_update_result()
    │       │
    │       └── No → _handle_fresh_install()
    │                   │
    │                   ├── resolver.resolve()
    │                   └── install_kit_to_project()
```

## Multi-Source Resolution

The `KitResolver` chains multiple sources:

```python
resolver = KitResolver(sources=[
    BundledKitSource(),      # Built-in kits
    StandalonePackageSource(), # External packages
])
```

Resolution iterates sources in order, returning the first match.

## Atomic Hook Updates

Hook installation uses atomic operations with rollback:

```
_perform_atomic_hook_update()
    │
    ├── Backup current settings.json
    ├── Backup current hooks directory
    │
    ├── Try:
    │   ├── remove_hooks()
    │   └── install_hooks()
    │
    └── On failure:
        ├── Restore settings.json
        └── Restore hooks directory
```

This prevents partial state where old hooks are removed but new hooks fail to install.

## Exception Hierarchy

```
DotAgentNonIdealStateException
    │
    ├── KitResolutionError
    │   ├── KitNotFoundError        # Kit doesn't exist in any source
    │   ├── ResolverNotConfiguredError  # No source can handle the request
    │   ├── SourceAccessError       # Network/filesystem access failed
    │   ├── KitManifestError        # Manifest parsing failed
    │   ├── KitVersionError         # Version mismatch/invalid
    │   ├── SourceFormatError       # Invalid source specification
    │   ├── KitConfigurationError   # General config issues
    │   └── InvalidKitIdError       # ID format violation
    │
    ├── HookConfigurationError      # Hook config issues
    └── ArtifactConflictError       # File already exists
```

All exceptions inherit from `DotAgentNonIdealStateException` for clean CLI error display.

## Key Implementation Details

### Version Comparison

Currently uses simple string comparison (`!=`). Version format is not enforced, but semantic versioning is recommended.

### Config Persistence

- Project config stored in `.claude/kits.json`
- Settings stored in `.claude/settings.json`
- Both updated atomically per operation

### Registry Updates

After installation, the registry is updated (non-blocking):

1. Generate registry entry content
2. Create kit-specific registry file
3. Add kit to main registry (fresh install only)

Registry failures are warnings, not errors.

## See Also

- [CLI Reference](cli-reference.md) - User-facing command documentation
- [Code Architecture](code-architecture.md) - General kit code structure
