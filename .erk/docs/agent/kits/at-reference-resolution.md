---
title: At-Reference Resolution in Kit Sources
read_when:
  - "erk md check fails with @ reference errors in kit sources"
  - "wondering why kit-md-check excludes --check-links"
  - "writing @ references in kit source files"
  - "understanding kit source vs installed artifact paths"
---

# @ Reference Resolution in Kit Sources

@ references in kit source files resolve differently than @ references in installed artifacts.

## The Problem

Source files live in `.claude/`, `.erk/docs/kits/`, etc. (source of truth). When kit artifacts are built to `packages/erk-kits/data/kits/<kit>/`, the @ references in those files are preserved as-is, written for the **installed** location.

## Why This Matters

When you write an @ reference in a kit command like:

```markdown
@../../../.erk/docs/kits/erk/includes/conflict-resolution.md
```

This path is:

- **Invalid from source location** - The source file is 6+ levels deep in the packages directory; `../../../` doesn't reach `.erk/`
- **Valid from installed location** - After installation to `.claude/commands/erk/auto-restack.md`, the relative path correctly reaches `.erk/docs/kits/`

## Implications for Validation

1. **`erk md check --check-links` cannot validate @ references in kit source directories** - The paths only make sense post-installation
2. **The Makefile's `kit-md-check` target excludes `--check-links`** for this reason
3. **@ reference validation only works after building** via `erk dev kit-build`

## Example

In `packages/erk-kits/.../erk/commands/erk/auto-restack.md`:

```markdown
@../../../.erk/docs/kits/erk/includes/conflict-resolution.md
```

Path resolution:

| Context         | Starting Point                                      | Result              |
| --------------- | --------------------------------------------------- | ------------------- |
| Source location | `packages/erk-kits/data/kits/erk/commands/erk/*.md` | Invalid (6+ levels) |
| Installed       | `.claude/commands/erk/auto-restack.md`              | Valid               |

## Best Practices

1. **Write @ references for the source location** - Since source files are now in `.claude/` and `.erk/docs/kits/`, paths work directly
2. **Test after building** - Run `erk dev kit-build` then `erk md check --check-links` on the project
3. **Use absolute paths when possible** - `@.erk/docs/kits/foo/bar.md` is clearer than relative paths

## Validation Workflow

```bash
# After modifying source files:
erk dev kit-build              # Build artifacts to kit packages
erk md check --check-links     # Validate @ references
```

## Related Documentation

- [Kit Documentation Installation Architecture](doc-installation.md) - Where docs get installed
- [Artifact Path Transformation](artifact-path-transformation.md) - Path transformation during installation
