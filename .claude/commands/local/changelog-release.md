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
5. Bumps version in pyproject.toml

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

**Default behavior:** Increment the **patch** version (X.Y.Z → X.Y.Z+1).

For example: if current version is 0.4.7, the next version is 0.4.8.

**Ask about minor releases:** Before proceeding, ask the user:

> "This will create version X.Y.Z+1. Should this be a **minor release** (X.Y+1.0) instead?
>
> A minor release is appropriate when:
>
> - Multiple significant features have accumulated across patch releases
> - You want to consolidate the previous minor version series (e.g., all of 0.4.x)
> - The release warrants a Release Overview summarizing major themes"

If the user confirms a minor release, use X.Y+1.0 (e.g., 0.4.7 → 0.5.0).

**Semver reference (pre-1.0):**

- **MINOR** (0.X.0): New functionality, milestone releases
- **PATCH** (0.0.X): Bug fixes, incremental improvements

### Phase 3b: Minor Release Workflow (if applicable)

If creating a minor release, add a **Release Overview** section that consolidates the major themes from the previous minor version series.

**Step 1: Identify themes**

Review the previous minor version series in CHANGELOG.md (e.g., 0.4.0 through 0.4.7) and identify 3-5 major feature themes that span multiple patches.

**Step 2: Write Release Overview**

Add a `### Release Overview` section immediately after the version header. Structure it as:

```markdown
## [0.5.0] - 2025-12-20 14:30 PT

### Release Overview

Brief 1-2 sentence summary of what this release represents.

#### Theme Name 1

**What it solves:** The problem this feature addresses.

**How it works:** Brief technical explanation.

**Key features:** User-facing entry points (commands, flags, etc.).

#### Theme Name 2

[Same structure...]

---

_The sections below document changes in this specific version (since 0.4.7):_

### Added

...
```

**Step 3: Theme documentation guidance**

For each theme:

- **What it solves** - The user problem or workflow gap addressed
- **How it works** - High-level technical explanation (not implementation details)
- **Key features** - Commands, flags, or entry points users interact with

Distinguish between:

- **Completeable objectives** - Features that solve a finite problem
- **Ongoing objectives** - Infrastructure improvements that continue to evolve

**Step 4: Consolidate under themes**

The detailed Added/Changed/Fixed/Removed sections follow the Release Overview. These document only the incremental changes since the last patch version, prefixed with a note clarifying they're not the full minor release content.

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
erk-dev bump-version {new_version}
```

### Phase 6: Summary and Next Steps

Report what was done and what's next:

```
Release {version} prepared:
- CHANGELOG.md updated with version {version}
- pyproject.toml bumped to {version}

Next steps (see RELEASING.md for full details):
1. Update required version file:
   echo "{version}" > .erk/required-erk-uv-tool-version
2. Squash, commit, and tag:
   uv sync && git add -A
   git reset --soft master
   git commit -m "Release {version}"
   erk-dev release-tag
3. Run CI locally: make all-ci
4. Push branch for GitHub CI: git push origin release-{version}
5. CHECKPOINT: Verify local + GitHub CI pass before proceeding
6. Publish: make publish
7. Merge to master after confirming publish works
```

### Output Format

**Start**: "Preparing release..."

**Version prompt**: Ask user to confirm version

**Progress**: Report each step as it completes

**Complete**: Summary with next steps
