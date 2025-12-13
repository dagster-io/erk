---
description: Sync CHANGELOG.md unreleased section with commits since last update
---

# /local:changelog-update

Brings the CHANGELOG.md Unreleased section up-to-date with the current commit.

> **Note:** Run this regularly during development. At release time, use `/local:changelog-release`.

## Usage

```bash
/local:changelog-update
```

## What It Does

1. Reads the "As of" marker in the Unreleased section
2. Finds commits since that marker (or since current version tag)
3. Categorizes and adds new entries with commit hashes
4. Updates the "As of" marker to current HEAD

---

## Agent Instructions

### Phase 1: Get Current State

Get the current HEAD commit:

```bash
git rev-parse --short HEAD
```

Read CHANGELOG.md and find the Unreleased section. Look for:

1. The "As of" line (e.g., `As of b5e949b45`) - extract the commit hash
2. If no "As of" marker, get the current version tag:

```bash
erk-dev release-info --json-output
```

Use `current_version_tag` as the starting point. If no tag exists either, this is likely a first-time setup.

### Phase 2: Get New Commits

Get commits between the marker and HEAD:

```bash
git log --oneline <marker_commit>..HEAD -- . ':!.claude' ':!.erk/docs/agent' ':!.impl'
```

If using a tag instead of "As of" marker:

```bash
git log --oneline <current_version_tag>..HEAD -- . ':!.claude' ':!.erk/docs/agent' ':!.impl'
```

If no new commits exist, report "CHANGELOG.md is already up-to-date" and exit.

### Phase 3: Categorize Commits

Group commits by type based on their messages:

**Major Changes** (significant features or breaking changes):

- New systems, major capabilities, or architectural improvements
- Breaking changes that users need to know about
- Features that warrant special attention in release notes

**Added** (new features):

- Commits with "add", "new", "implement", "create" in message
- Feature PRs

**Changed** (improvements):

- Commits with "improve", "update", "enhance", "move", "migrate" in message
- Non-breaking changes to existing functionality

**Fixed** (bug fixes):

- Commits with "fix", "bug", "resolve", "correct" in message
- Issue fixes

**Removed** (removals):

- Commits with "remove", "delete", "drop" in message

**Filter out** (do not include):

- CI/CD-only changes (unless they affect users)
- Documentation-only changes (docs/, .md files in .erk/)
- Test-only changes
- Merge commits
- Internal-only refactors that don't affect user-facing behavior (commits with "refactor" that only change internal structure)

### Phase 4: Format Entries

Format each entry as:

```markdown
- Brief user-facing description (commit_hash)
```

Guidelines:

- Focus on **user benefit**, not implementation details
- Start with a verb (Add, Fix, Improve, Remove, Move, Migrate)
- Be concise but clear (1 sentence)
- Include the short commit hash in parentheses
- Use "Major Changes" section for significant user-facing features (new systems, breaking changes)

### Phase 5: Update CHANGELOG.md

Update the Unreleased section:

1. **Update "As of" line** to current HEAD commit hash
2. **Add new entries** under appropriate category headers
3. **Preserve existing entries** - do not remove or modify them
4. **Create category headers** only if they have new entries

Category order (if present):

1. Major Changes
2. Added
3. Changed
4. Fixed
5. Removed

If a category header already exists, append new entries below existing ones.

### Phase 6: Report

Report summary:

- Number of new commits processed
- Number of entries added (some commits may be filtered out)
- Categories updated
- New "As of" commit hash

### Output Format

**Start**: "Checking for new commits since last changelog sync..."

**No changes**: "CHANGELOG.md is already up-to-date (as of {commit})"

**With changes**:

```
Updated CHANGELOG.md:
- Processed {n} commits
- Added {m} entries to: {categories}
- Now as of {commit}
```
