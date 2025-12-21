---
title: At-Reference Resolution in Kit Artifacts
read_when:
  - "erk md check fails with @ reference errors in kit artifacts"
  - "wondering why kit-md-check excludes --check-links"
  - "writing @ references in kit artifact files"
  - "understanding kit artifact vs installed artifact paths"
---

# @ Reference Resolution in Kit Artifacts

@ references in kit artifacts (stored in packages) resolve differently than @ references in installed artifacts.

## The Problem

Kit artifacts live in `packages/erk-kits/data/kits/<kit>/`. When they're installed to `.claude/`, `.erk/docs/`, etc., the @ references in those files are preserved as-is, written for the **installed** location.

## Why This Matters

When you write an @ reference in a kit command like:

```markdown
@../../../.erk/docs/kits/erk/includes/conflict-resolution.md
```

This path is:

- **Invalid from package location** - The artifact is 6+ levels deep in the packages directory; `../../../` doesn't reach `.erk/`
- **Valid from installed location** - After installation to `.claude/commands/erk/auto-restack.md`, the relative path correctly reaches `.erk/docs/kits/`

## Implications for Validation

1. **`erk md check --check-links` cannot validate @ references in kit package directories** - The paths only make sense post-installation
2. **The Makefile's `kit-md-check` target excludes `--check-links`** for this reason
3. **@ reference validation only works after installation** via `erk kit install`

## Example

In `packages/erk-kits/.../erk/commands/erk/auto-restack.md`:

```markdown
@../../../.erk/docs/kits/erk/includes/conflict-resolution.md
```

Path resolution:

| Context          | Starting Point                                      | Result              |
| ---------------- | --------------------------------------------------- | ------------------- |
| Package location | `packages/erk-kits/data/kits/erk/commands/erk/*.md` | Invalid (6+ levels) |
| Installed        | `.claude/commands/erk/auto-restack.md`              | Valid               |

## Best Practices

1. **Write @ references for the installed location** - Paths should work from `.claude/` or `.erk/` after installation
2. **Test after installing** - Run `erk kit install --all` then `erk md check --check-links` on the project
3. **Use absolute paths when possible** - `@.erk/docs/kits/foo/bar.md` is clearer than relative paths

## Validation Workflow

```bash
# After modifying kit artifacts:
erk kit install --all         # Install all kits to project
erk md check --check-links    # Validate @ references
```

## Related Documentation

- [Kit Documentation Installation Architecture](doc-installation.md) - Where docs get installed
- [Artifact Path Transformation](artifact-path-transformation.md) - Path transformation during installation
