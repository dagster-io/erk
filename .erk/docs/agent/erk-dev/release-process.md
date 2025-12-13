---
title: Release Process
read_when:
  - "releasing a new version of erk"
  - "creating version tags"
  - "understanding the erk release workflow"
---

# Release Process

## Commands

### erk-dev release-info

Get current version and last release info from CHANGELOG.md:

```bash
erk-dev release-info           # Text output
erk-dev release-info --json-output  # JSON for automation
```

### erk-dev release-tag

Create and optionally push a version tag:

```bash
erk-dev release-tag            # Create tag only
erk-dev release-tag --push     # Create and push
erk-dev release-tag --dry-run  # Preview without changes
```

## Workflow

1. Update CHANGELOG.md with release notes
2. Run `/local:changelog-release` to finalize version
3. Run `erk-dev release-tag --push` to create and push tag
4. CI handles the rest (PyPI publish, etc.)
