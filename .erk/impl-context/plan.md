# Release 0.9.0

## Context

Releasing erk 0.9.0. The Unreleased section has major changes (erk pr consolidation, plan ID removal from branches, default backend switch to draft PR) plus many additions, fixes, and removals. Following RELEASING.md step-by-step.

## Steps

### 1. Create release branch
```bash
gt create release-0.9.0 -a --no-interactive
```

### 2. Sync changelog
```
/local:changelog-update
```

### 3. Finalize changelog and version
```
/local:changelog-release
```
- Version: 0.9.0
- Moves Unreleased to versioned section, strips hashes, bumps pyproject.toml

### 4. Update required version file
```bash
echo "0.9.0" > .erk/required-erk-uv-tool-version
```

### 5. Squash, commit, and tag
```bash
uv sync
git add -A
git tag -d v0.9.0 2>/dev/null
git reset --soft master
git commit -m "Release 0.9.0"
erk-dev release-tag
```

### 6. Run CI locally
```bash
make all-ci
```

### 7. Push and create PR
```bash
erk pr submit
```

### 8. Confirmation checkpoint
Wait for user to confirm local + GitHub CI pass, version correct, tag exists.

### 9. Publish to PyPI
```bash
make publish
```

### 10. Merge to master
```bash
RELEASE_BRANCH=$(git branch --show-current)
git checkout master
git pull origin master
git merge "$RELEASE_BRANCH" --no-edit
git push origin master --tags
```

## Key Files
- `pyproject.toml` — version field
- `CHANGELOG.md` — release notes
- `.erk/required-erk-uv-tool-version` — version check file
