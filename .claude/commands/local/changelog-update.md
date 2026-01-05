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

1. Reads the "As of" marker in the Unreleased section (adds one if missing)
2. Finds commits on master since that marker
3. Categorizes commits and presents proposal for user review
4. Updates changelog only after user approval
5. Always updates the "As of" marker to current HEAD (even if no new entries)

---

## Agent Instructions

### Phase 1-2: Get Commits Since Last Sync

Run the changelog-commits command to get all commits since the last "As of" marker:

```bash
erk-dev changelog-commits --json-output
```

This command:

- Parses CHANGELOG.md to find the "As of <commit>" marker
- Gets commits using `--first-parent` (excludes feature branch commits)
- Excludes paths: `.claude/`, `docs/learned/`, `.impl/`
- Returns JSON with commit details including PR numbers

**JSON output structure:**

```json
{
  "success": true,
  "since_commit": "b6a2bb40b",
  "head_commit": "af8fa25c9",
  "commits": [
    {
      "hash": "af8fa25c9",
      "subject": "Fix artifact sync... (#3619)",
      "body": "...",
      "files_changed": ["src/erk/artifacts/sync.py", ...],
      "pr_number": 3619
    }
  ]
}
```

If `success` is false and error indicates missing "As of" marker:

1. Read the CHANGELOG.md to find the most recent release version (e.g., `## [0.3.3]`)
2. Use `git log --oneline -1 --grep="X.Y.Z"` to find the release commit hash
3. Get commits since that release using `erk-dev changelog-commits --since <release-hash> --json-output`
4. Continue to Phase 3 to categorize and present those commits

**Important:** A missing marker means the Unreleased section needs all commits since the last release, not just an empty marker at HEAD. The `--since` option allows you to specify a commit directly when no marker exists.

If `success` is false for other reasons, display the error message and exit.

If `commits` array is empty, the changelog content is current but the marker should still be updated:

1. Update the "As of" line to the current HEAD commit hash
2. Report "CHANGELOG.md is already up-to-date. Updated marker to {head_commit}." and exit

### Phase 3: Analyze and Categorize Commits

Use the commit details from the JSON output (subject, body, files_changed) to categorize each commit.

#### Categories

**Major Changes** (significant features or breaking changes):

- New systems, major capabilities, or architectural improvements
- Breaking changes that users need to know about
- CLI command reorganization or removal
- Features that warrant special attention in release notes

**Major Change Entry Requirements:**

When writing a Major Change entry, always include:

1. **What it does** - Brief description of the feature/change
2. **Motivation/purpose** - Why we built it, the problem it solves
3. **Value to user** - What benefit users get from this

**Merge related commits:** Roll up all related commits (fixes, aliases, extensions) into a single Major Change entry with explanatory prose. Don't list implementation details or internal commits separately.

**Never expose implementation details** like function names, internal checks, or architecture patterns. Focus on user-visible behavior and benefits.

Example format:

```markdown
- **Feature name**: Brief description of what it does. Motivation explaining why we built it. Value statement about user benefit. (primary_commit_hash)
```

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

**Always filter:**

- **Release housekeeping** - version bumps ("Bump version to X"), CHANGELOG finalization, lock file updates for releases
- CI/CD-only changes (.github/workflows/)
- Documentation-only changes (docs/, .md files in .erk/)
- Test-only changes (tests/)
- Internal code conventions (frozen dataclasses, parameter defaults)
- Local-only commands (`.claude/commands/local/`)
- Gateway method additions (abc.py + real.py + fake.py pattern)
- Build tooling (Makefile, pyproject.toml deps)
- Merge commits with no substantive changes
- Internal-only refactors that don't affect user-facing behavior
- Infrastructure/architecture changes invisible to users
- Vague commit messages like "update", "WIP", "wip"

**Likely internal (verify before including):**

- "Refactor", "Relocate", "Consolidate" - check if user-visible
- Skill/agent documentation updates - usually internal
- "Harden", "Strengthen" - usually internal enforcement

#### Internal-Only Patterns (always filter)

**By path:**

- Changes only in `tests/` → internal
- Changes only in `scripts/` (unless CLI-facing) → internal
- Changes only to `**/fake*.py` → internal
- Changes only to `Makefile` → internal
- Changes only to `.github/workflows/` → internal

**By content:**

- Gateway ABC method additions (`abc.py`, `real.py`, `fake.py`, `dry_run.py`, `printing.py`) → internal
- Code convention migrations (frozen dataclasses, default params) → internal
- Import reorganization → internal
- Hook/skill/command in `.claude/commands/local/` → internal (local-only)

**By commit message:**

- "Refactor X to Y" with no user-visible change → internal
- "Consolidate", "Relocate", "Migrate" internal modules → internal
- "Eliminate default parameter values" → internal
- "Migrate dataclasses to frozen=True" → internal

#### Roll-Up Detection

When multiple commits are part of a larger initiative, group them under a single Major Change entry:

**Detection patterns:**

- Multiple commits mentioning same keyword (e.g., "kit", "artifact", "hook")
- Commits with sequential PR numbers on same topic
- Commits that reference same GitHub issue/objective

**Roll-up examples:**

- 5+ commits about "kit" removal → "Eliminate kit infrastructure entirely"
- 3+ commits about "artifact sync" → "Add unified artifact distribution system"
- Multiple "objective skill" commits → single entry or filter entirely

**Presentation:**

When roll-up detected, present as:

```
**Detected Roll-Up:** {n} commits appear related to "{topic}"
Suggest consolidating into single Major Change: "{proposed description}"
Commits: {list of hashes}
```

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
