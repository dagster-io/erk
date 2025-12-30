---
description: Sync CHANGELOG.md unreleased section with commits since last update
---

# /local:changelog-update

Brings the CHANGELOG.md Unreleased section up-to-date with commits merged to master.

> **Note:** Run this regularly during development. At release time, use `/local:changelog-release`.

## Usage

```bash
/local:changelog-update
```

## What It Does

1. Reads the "As of" marker in the Unreleased section
2. Finds commits on master since that marker
3. Categorizes commits and presents proposal for user review
4. Updates changelog only after user approval

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

**IMPORTANT: Only include commits that are on master.** Use `--first-parent` to follow only the first parent (merge commits), which excludes commits from feature branches that haven't been squash-merged.

Get commits between the marker and HEAD on master:

```bash
git log --oneline --first-parent <marker_commit>..HEAD -- . ':!.claude' ':!docs/learned' ':!.impl'
```

If using a tag instead of "As of" marker:

```bash
git log --oneline --first-parent <current_version_tag>..HEAD -- . ':!.claude' ':!docs/learned' ':!.impl'
```

If no new commits exist, report "CHANGELOG.md is already up-to-date" and exit.

### Phase 3: Analyze and Categorize Commits

For each commit, fetch additional context to understand its scope:

```bash
git show --stat --format="%s%n%n%b" <commit_hash> | head -40
```

#### Categories

**Major Changes** (significant features or breaking changes):

- New systems, major capabilities, or architectural improvements
- Breaking changes that users need to know about
- CLI command reorganization or removal
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

#### Filter Out (do not include)

- **Release housekeeping** - version bumps ("Bump version to X"), CHANGELOG finalization, lock file updates for releases
- CI/CD-only changes (unless they affect users)
- Documentation-only changes (docs/, .md files in .erk/)
- Test-only changes
- Merge commits with no substantive changes
- Internal-only refactors that don't affect user-facing behavior
- Infrastructure/architecture changes invisible to users
- Vague commit messages like "update", "WIP", "wip"

### Phase 4: Present Proposal for Review

**CRITICAL: Do NOT edit the changelog yet. Present the proposal and wait for user approval.**

Format the proposal as follows:

```
Found {n} commits since last sync ({marker_commit}).

**Proposed Entries:**

**Major Changes ({count}):**
1. `{hash}` - {proposed description}
   - Reasoning: {why this is a major change}

**Added ({count}):**
1. `{hash}` - {proposed description}
   - Reasoning: {why categorized as Added}

**Changed ({count}):**
...

**Fixed ({count}):**
...

**Removed ({count}):**
...

**Filtered Out ({count}):**
- `{hash}` - "{original message}" → {reason for filtering}

---

**Low-Confidence Categorizations:** ⚠️
- `{hash}` - Categorized as {category}, but could be {alternative}
  - Uncertainty: {explanation of ambiguity}

---

Would you like me to:
1. Adjust any categorizations?
2. Rephrase any entry descriptions?
3. Include or exclude any commits?
```

#### Confidence Flags

Mark entries as **low-confidence** when:

- Commit message is ambiguous (e.g., "update X" could be Changed or internal)
- Scope is unclear (could be user-facing or internal-only)
- Category is borderline (e.g., "Add X" but it's really a refactor)
- Large architectural changes that might or might not affect users
- Commits that touch both user-facing and internal code

### Phase 5: Update CHANGELOG.md (After Approval)

Only proceed after the user confirms or provides adjustments.

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

After successful update:

```
Updated CHANGELOG.md:
- Processed {n} commits
- Added {m} entries to: {categories}
- Now as of {commit}
```

### Entry Format

Format each entry as:

```markdown
- Brief user-facing description (commit_hash)
```

Guidelines:

- Focus on **user benefit**, not implementation details
- Start with a verb (Add, Fix, Improve, Remove, Move, Migrate)
- Be concise but clear (1 sentence)
- Include the short commit hash in parentheses
- Add notes for entries that may cause user-visible issues (e.g., "note: this may cause hard failures, please report if encountered")
