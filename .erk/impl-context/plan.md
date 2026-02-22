# Fix Release Process Documentation

## Context

The 0.8.0 release hit three preventable issues in the RELEASING.md process:

1. **Branch naming**: `release/0.8.0` (slash) caused Graphite `refs/gt-fetch-head/release` conflict because git can't have both a ref and a child ref at the same path. Historical convention was `release-X.Y.Z` (hyphens) but this wasn't documented.

2. **Merge-to-master step used `source .erk/bin/activate.sh`**: This activates the venv/directory but does NOT switch git branches. Running `git reset --hard origin/master` while still on `release/0.8.0` blew away the release commit. The tag saved us.

3. **`erk prepare` referenced but removed**: Step 9's comment and the Prerequisites still reference `erk prepare`, which was removed in this release cycle.

## Changes

**File:** `RELEASING.md`

### Prerequisites section (already fixed)
- Replace `erk prepare` with `gt create` / `git checkout -b` — already done during this session.

### Step 9: Merge to Master
Replace the `source .erk/bin/activate.sh` one-liner with explicit git commands:

```bash
RELEASE_BRANCH=$(git branch --show-current)
git checkout master
git pull origin master
git merge "$RELEASE_BRANCH" --no-edit
git push origin master --tags
```

Add a warning that `source .erk/bin/activate.sh` does NOT switch branches.

### Add "Troubleshooting" section
Document the two gotchas we hit:
- Graphite ref conflicts from slash-named branches → use hyphens
- Activate script doesn't switch branches → use explicit `git checkout`

## Verification

- Read the updated RELEASING.md and confirm all steps are self-consistent
- Verify no remaining references to `erk prepare`
