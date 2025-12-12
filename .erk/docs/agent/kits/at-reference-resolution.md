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

Kit source files live in `packages/erk-kits/src/erk_kits/data/kits/<kit>/`. When these files use @ references, they're written for the **installed** location (`.claude/` or `.erk/`), not the source location.

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
3. **@ reference validation only works after installation** via `erk kit sync`

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

1. **Write @ references for installed location** - Always write paths as if the file is already in `.claude/` or `.erk/docs/kits/`
2. **Test after installation** - Run `erk kit sync --force` then `erk md check --check-links` on the project
3. **Use absolute paths when possible** - `@.erk/docs/kits/foo/bar.md` is clearer than relative paths

## Validation Workflow

```bash
# After modifying kit source files:
erk kit sync --force           # Install/update kit artifacts
erk md check --check-links     # Now validate @ references
```

## Related Documentation

- [Kit Documentation Installation Architecture](doc-installation.md) - Where docs get installed
- [Artifact Path Transformation](artifact-path-transformation.md) - Path transformation during installation
