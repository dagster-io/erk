---
description: Finalize changelog and create a new release version
---

# /local:changelog-release

Finalizes the Unreleased section and creates a new versioned release.

> **Prerequisite:** The Unreleased section should be up-to-date. Run `/local:changelog-update` first if needed.

## Usage

```bash
/local:changelog-release
```

## What It Does

1. Ensures Unreleased section is current (runs changelog-update)
2. Determines the next version number
3. Moves Unreleased content to a new versioned section
4. Removes commit hashes from entries
5. Creates a git tag for the release

---

## Agent Instructions

### Phase 1: Ensure Changelog is Current

First, sync the changelog with the latest commits:

```bash
git rev-parse --short HEAD
```

Read CHANGELOG.md and check the "As of" marker. If it doesn't match HEAD, run the changelog-update workflow first (or prompt user to run `/local:changelog-update`).

### Phase 2: Get Release Info

```bash
erk-dev release-info --json-output
```

This returns:

- `current_version`: Version from pyproject.toml
- `current_version_tag`: Tag if it exists (should be null if releasing)
- `last_version`: Most recent release in CHANGELOG.md

### Phase 3: Determine Next Version

Always increment the **patch** version (X.Y.Z+1). Do not prompt the user - just use the next patch version automatically.

For example: if current version is 0.2.6, the next version is 0.2.7.

### Phase 4: Move Unreleased to Versioned Section

Transform the CHANGELOG.md:

**Before:**

```markdown
## [Unreleased]

As of abc1234

### Changed

- Improve hook message clarity (b5e949b45)
- Move CHANGELOG to repo root (1fe3629bf)

## [0.2.6] - 2025-12-12 14:30 PT
```

**After:**

```markdown
## [Unreleased]

## [0.2.7] - 2025-12-13 HH:MM PT

### Changed

- Improve hook message clarity
- Move CHANGELOG to repo root

## [0.2.6] - 2025-12-12 14:30 PT
```

Steps:

1. **Remove** the "As of" line entirely
2. **Create new version header** with format: `## [{version}] - {date} HH:MM PT`
   - Get current time in Pacific: Use current datetime
3. **Remove commit hashes** from all entries (strip ` (abc1234)` suffixes)
4. **Keep Unreleased section** empty (just the header)

### Phase 5: Update Version in pyproject.toml

Use the CLI to bump the version:

```bash
erk-dev bump-version --version {new_version}
```

### Phase 6: Create Git Tag

After the changes are made, create the version tag:

```bash
erk-dev release-tag
```

This creates an annotated tag `v{new_version}`.

### Phase 7: Summary and Next Steps

Report what was done and what's next:

```
Release {version} prepared:
- CHANGELOG.md updated with version {version}
- pyproject.toml bumped to {version}
- Tag v{version} created

Next steps:
1. Review the changes: git diff
2. Commit: git commit -am "Release {version}"
3. Push with tag: git push && git push --tags
```

### Output Format

**Start**: "Preparing release..."

**Version prompt**: Ask user to confirm version

**Progress**: Report each step as it completes

**Complete**: Summary with next steps
