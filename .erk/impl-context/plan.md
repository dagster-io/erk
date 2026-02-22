# Release Plan

## Context

Release the next version of erk. Current version is 0.8.0. The Unreleased section of CHANGELOG.md has new features (branch name slugs, `--env` flag, `-f/--force` flag), a change (abbreviated stage names), and a fix (objective prose reconciliation). This looks like a minor release (0.9.0) given the new features, but the user will confirm the version number.

## Steps

Follow RELEASING.md exactly:

### 1. Create release branch
```bash
gt create release-X.Y.Z -a --no-interactive
```
(Version TBD after user confirms)

### 2. Sync Changelog
Run `/local:changelog-update` to sync Unreleased section with any commits since last update.

### 3. Finalize Changelog and Version
Run `/local:changelog-release` which prompts for version, moves Unreleased to versioned section, strips hashes, bumps pyproject.toml.

### 4. Update Required Version File
```bash
echo "X.Y.Z" > .erk/required-erk-uv-tool-version
```

### 5. Squash, Commit, and Tag
```bash
uv sync
git add -A
git tag -d vX.Y.Z 2>/dev/null
git reset --soft master
git commit -m "Release X.Y.Z"
erk-dev release-tag
```

### 6. Run CI Locally
Run `make all-ci` via devrun agent.

### 7. Push and Create PR
Run `erk pr submit` to push branch and create PR for GitHub CI.

### 8. Confirmation Checkpoint
Wait for user to verify local + GitHub CI pass before proceeding.

### 9. Publish to PyPI
```bash
make publish
```

### 10. Merge to Master
```bash
RELEASE_BRANCH=$(git branch --show-current)
git checkout master
git pull origin master
git merge "$RELEASE_BRANCH" --no-edit
git push origin master --tags
```

## Key Files
- `pyproject.toml` - version number
- `CHANGELOG.md` - release notes
- `.erk/required-erk-uv-tool-version` - required version file
