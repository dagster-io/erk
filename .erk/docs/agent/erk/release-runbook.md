---
title: Release Runbook
read_when:
  - "releasing a new version of erk"
  - "publishing to PyPI or GitHub releases"
  - "updating CHANGELOG.md for a release"
  - "bumping version numbers"
---

# Release Runbook

How to publish a new erk release.

## Prerequisites

- All PRs for the release merged to master
- CI passing on master

## Steps

### 1. Draft Release Notes

```bash
/erk:draft-release-notes
```

This analyzes commits, categorizes changes, and updates CHANGELOG.md with your approval.

### 2. Bump Version

```bash
erk-dev bump-version X.Y.Z
```

### 3. Create Release PR

```bash
erk pr submit "Release vX.Y.Z"
```

This creates a PR with the version bump and changelog updates. Merge it to master once CI passes.

### 4. Create GitHub Release

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file /tmp/release-notes.md
```

Or create via GitHub UI at https://github.com/dagster-io/erk/releases/new

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Patch** (0.2.1 → 0.2.2): Bug fixes only
- **Minor** (0.2.2 → 0.3.0): New features, backwards compatible
- **Major** (0.3.0 → 1.0.0): Breaking changes

## Verification

After release:

```bash
# Check version displays correctly
erk --version

# Check release notes are accessible
erk info release-notes
```

## Tooling Reference

| Command                    | Purpose                              |
| -------------------------- | ------------------------------------ |
| `erk-dev release-info`     | Get current/last version info        |
| `erk-dev release-update`   | Update CHANGELOG.md programmatically |
| `erk info release-notes`   | View changelog entries               |
| `/erk:draft-release-notes` | AI-assisted release notes drafting   |
