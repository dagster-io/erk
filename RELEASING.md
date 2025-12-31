# Releasing

How to publish a new erk release.

## Prerequisites

- All PRs for the release merged to master
- CI passing on master
- On the master branch (or ready to create a release branch from it)

## Ongoing: Keep Changelog Current

Run this regularly during development (after merging PRs, completing features):

```bash
/local:changelog-update
```

This syncs the Unreleased section with commits since the last update, adding entries with commit hashes for traceability.

## Release Steps

### 1. Create a Release Branch

```bash
git checkout -b release-X.Y.Z
```

Release work happens on a dedicated branch, not directly on master.

### 2. Finalize Changelog and Version

```bash
/local:changelog-release
```

This command:

- Ensures changelog is current (runs changelog-update if needed)
- Prompts for version number
- Moves Unreleased content to a versioned section
- Strips commit hashes from entries
- Bumps version in pyproject.toml

### 3. Squash, Commit, and Tag

Squash all release prep commits into a single release commit:

```bash
uv sync
git add -A
git tag -d vX.Y.Z 2>/dev/null  # Delete premature tag if exists
git reset --soft master
git commit -m "Release X.Y.Z"
erk-dev release-tag
```

This ensures a clean single commit for the release with the tag pointing to it.

### 4. Publish to PyPI

```bash
make publish
```

This builds and publishes all packages to PyPI in dependency order.

### 5. Merge to Master

After confirming the publish succeeded:

```bash
git checkout master
git merge release-X.Y.Z
git push origin master --tags
```

Only merge to master after verifying the release works correctly.

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
