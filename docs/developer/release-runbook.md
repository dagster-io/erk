# Release Runbook

How to publish a new erk release.

## Prerequisites

- All PRs for the release merged to master
- CI passing on master

## Ongoing: Keep Changelog Current

Run this regularly during development (after merging PRs, completing features):

```bash
/local:changelog-update
```

This syncs the Unreleased section with commits since the last update, adding entries with commit hashes for traceability.

## Release Steps

### 1. Finalize Changelog and Version

```bash
/local:changelog-release
```

This command:

- Ensures changelog is current (runs changelog-update if needed)
- Prompts for version number
- Moves Unreleased content to a versioned section
- Strips commit hashes from entries
- Bumps version in pyproject.toml
- Creates git tag `vX.Y.Z`

### 2. Create Release PR

```bash
erk pr submit "Release vX.Y.Z"
```

This creates a PR with the version bump and changelog updates. Merge it to master once CI passes.

### 3. Publish to PyPI

```bash
make publish
```

This builds and publishes all packages to PyPI in dependency order.

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

| Command                    | Purpose                                     |
| -------------------------- | ------------------------------------------- |
| `/local:changelog-update`  | Sync Unreleased section with latest commits |
| `/local:changelog-release` | Finalize release (version, tag, cleanup)    |
| `erk-dev release-info`     | Get current/last version info               |
| `erk-dev release-tag`      | Create git tag for current version          |
| `erk-dev release-update`   | Update CHANGELOG.md programmatically        |
| `erk info release-notes`   | View changelog entries                      |
