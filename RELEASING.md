# Releasing

How to publish a new erk release.

## Prerequisites

- All PRs for the release merged to master
- CI passing on master
- Create a release branch (use hyphen, not slash):
  - With Graphite: `gt create release-X.Y.Z -a`
  - Without Graphite: `git checkout -b release-X.Y.Z`

## Release Steps

### 1. Sync Changelog

```bash
/local:changelog-update
```

This syncs the Unreleased section with commits since the last update, adding entries with commit hashes for traceability.

### 2. Finalize Changelog and Version

```bash
/local:changelog-release
```

This command:

- Prompts for version number
- Moves Unreleased content to a versioned section
- Strips commit hashes from entries
- Bumps version in pyproject.toml

### 3. Update Required Version File

Update the required erk version to match the new release:

```bash
echo "X.Y.Z" > .erk/required-erk-uv-tool-version
```

This file is used by version checking to warn users when their installed erk doesn't match the repository's required version. Failing to update this will cause CI failures due to version mismatch warnings in shell integration tests.

### 4. Squash, Commit, and Tag

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

### 5. Run CI Locally

```bash
make all-ci
```

Verify all checks pass locally before pushing. This catches obvious issues early.

### 6. Push Branch and Create PR for GitHub CI

```bash
erk pr submit
```

This pushes the release branch and creates a PR for GitHub CI. Review the GitHub Actions results to catch any environment-specific issues.

### 7. Confirmation Checkpoint

**STOP and verify before publishing:**

- [ ] Local CI passes (`make all-ci`)
- [ ] GitHub CI passes (check Actions tab)
- [ ] Version number is correct in pyproject.toml
- [ ] CHANGELOG.md has correct version header
- [ ] Git tag exists and points to the release commit

Only proceed to publish after confirming all checks pass. Publishing to PyPI is irreversible.

> **Note for Claude:** Do NOT use `gh pr checks --watch` or similar commands to monitor CI. Instead, tell the user to check GitHub Actions manually and wait for their confirmation before proceeding.

### 8. Publish to PyPI

```bash
make publish
```

This builds and publishes all packages to PyPI in dependency order.

### 9. Merge to Master

After confirming the publish succeeded, merge the release branch into master:

```bash
RELEASE_BRANCH=$(git branch --show-current)
git checkout master
git pull origin master
git merge "$RELEASE_BRANCH" --no-edit
git push origin master --tags
```

> **Warning:** Do NOT use `source .erk/bin/activate.sh` to switch branches. The activate script sets up the venv and working directory but does NOT change the git branch. Running git commands after `activate.sh` will operate on whatever branch you were already on, not master.

Only merge to master after verifying the release works correctly.

## Troubleshooting

### Graphite ref conflicts from slash in branch names

Using `release/X.Y.Z` (with a slash) causes Graphite `refs/gt-fetch-head/release` conflicts because git cannot have both a ref and a child ref at the same path. Always use hyphens: `release-X.Y.Z`.

### Activate script does not switch git branches

`source .erk/bin/activate.sh` sets up the venv and working directory but does NOT change the current git branch. If you run `git reset --hard origin/master` while on a release branch, you will blow away the release commit. Always use explicit `git checkout master` before running git operations that target master.

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
