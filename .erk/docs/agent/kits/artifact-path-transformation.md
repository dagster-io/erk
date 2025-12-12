---
title: Kit Artifact Path Transformation Patterns
read_when:
  - "debugging kit artifact path mismatches"
  - "modifying kit artifact installation logic"
  - "understanding why doc artifacts have different path handling"
  - "fixing compare_artifact_lists or check_artifact_sync"
---

# Kit Artifact Path Transformation Patterns

The kit installation system uses path transformation logic that differs by artifact type. Understanding these patterns is essential when modifying kit artifact handling.

## Path Structure by Artifact Type

| Artifact Type | Source Path (in kit)  | Installed Path                |
| ------------- | --------------------- | ----------------------------- |
| command       | `commands/foo/bar.md` | `.claude/commands/foo/bar.md` |
| skill         | `skills/foo/SKILL.md` | `.claude/skills/foo/SKILL.md` |
| hook          | `hooks/foo.py`        | `.claude/hooks/foo.py`        |
| doc           | `docs/foo/bar.md`     | `.erk/docs/kits/foo/bar.md`   |
| workflow      | `workflows/foo.yml`   | `.github/workflows/foo.yml`   |

## Target Directory Mapping

The `ARTIFACT_TARGET_DIRS` constant in `erk/kits/models/artifact.py` defines the base directory for each artifact type:

| Type     | Base Directory   |
| -------- | ---------------- |
| skill    | `.claude`        |
| command  | `.claude`        |
| agent    | `.claude`        |
| hook     | `.claude`        |
| doc      | `.erk/docs/kits` |
| workflow | `.github`        |

## Key Implementation Details

### In `compare_artifact_lists()` (`src/erk/cli/commands/kit/check.py`)

This function compares manifest artifacts against installed artifacts:

1. **Doc type skips plural suffix** - The target directory `.erk/docs/kits` is complete, so no `docs/` subdirectory is added
2. **Other types add plural suffix** - e.g., `skill` → `.claude/skills/`, `command` → `.claude/commands/`
3. **Path prefix stripping** - Source paths like `commands/foo/bar.md` have the type prefix stripped before joining with target dir

### In `check_artifact_sync()`

When verifying artifacts are in sync with bundled sources:

1. **Installed path normalization** - Strip the base directory prefix (`.claude/`, `.erk/docs/kits/`, `.github/`)
2. **Doc type special handling** - When looking up bundled source for doc artifacts, must ADD `docs/` prefix back
   - Installed: `.erk/docs/kits/erk/includes/foo.md` → `erk/includes/foo.md` (normalized)
   - Bundled: `docs/erk/includes/foo.md` (with prefix added back)

## Common Pitfall

When comparing installed vs manifest artifacts for docs:

- **Wrong:** Concatenate without prefix handling → `.erk/docs/kits/docs/erk/...`
- **Right:** Strip type prefix from source path → `.erk/docs/kits/erk/...`

The source code comment in `check_artifact_sync()` explains this:

```
# For doc type artifacts, the bundled path has "docs/" prefix that was stripped
# during installation. We need to add it back for sync checking.
# Installed: .erk/docs/kits/erk/includes/foo.md -> erk/includes/foo.md
# Bundled: docs/erk/includes/foo.md
```

## Related Documentation

- [Artifact Synchronization](artifact-synchronization.md) - Version-based sync behavior
- [Kit Artifact and Symlink Management](dev/artifact-management.md) - Symlink handling during installation
