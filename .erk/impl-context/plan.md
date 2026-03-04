# Release Plan: erk 0.9.5

## Context

Current version is 0.9.4 (released 2026-03-02). There are substantial unreleased changes on master including a major new feature (stacked branches on same worktree / same-worktree plan implementation). Releasing as patch version: **0.9.4 → 0.9.5**.

## Steps

### 1. Create Release Branch

```bash
gt create release-0.9.5 -a --no-interactive
```

Use hyphens (not slashes) to avoid Graphite ref conflicts.

### 2. Sync Changelog

```
/local:changelog-update
```

Syncs Unreleased section with commits since last update.

### 3. Finalize Changelog and Version

```
/local:changelog-release
```

Prompts for version `0.9.5`, moves Unreleased → versioned section, strips commit hashes, bumps pyproject.toml.

### 4. Update Required Version File

```bash
echo "0.9.5" > .erk/required-erk-uv-tool-version
```

### 5. Squash, Commit, and Tag

```bash
uv sync
git add -A
git tag -d v0.9.5 2>/dev/null
git reset --soft master
git commit -m "Release 0.9.5"
erk-dev release-tag
```

### 6. Run CI Locally

```bash
make all-ci
```

### 7. Push and Create PR

```bash
erk pr submit
```

### 8. Confirmation Checkpoint (STOP)

Wait for user to confirm:
- [ ] Local CI passes
- [ ] GitHub CI passes
- [ ] Version correct in pyproject.toml
- [ ] CHANGELOG.md has `[0.9.5]` header
- [ ] Git tag exists

**Do NOT proceed to publish until user confirms all checks pass.**

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

## Verification

After release:
```bash
erk --version  # should show 0.9.5
erk info release-notes  # should show 0.9.5 entries
```
