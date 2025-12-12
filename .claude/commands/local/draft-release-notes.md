---
description: Audit commits and draft release notes for next version
---

# /local:draft-release-notes

Analyzes commits since the last version and drafts release notes for the next release.

> **Note:** Release notes can be viewed with `erk info release-notes`

## Usage

```bash
/local:draft-release-notes
```

## What It Does

1. Gets release info via `erk-dev release-info`
2. Finds commits since the last release
3. Groups them by type (features, fixes, improvements)
4. Drafts user-facing release notes
5. Asks for your review
6. Updates CHANGELOG.md via `erk-dev release-update`

---

## Agent Instructions

### Phase 1: Get Release Info

Use the deterministic CLI to get version information:

```bash
erk-dev release-info --json-output
```

This returns JSON with:

- `current_version`: Version from pyproject.toml (the version we're currently on)
- `last_version`: Most recent release in CHANGELOG.md
- `last_date`: Date of that release (YYYY-MM-DD)

**Important**: We are drafting release notes for the **next** version, not the current version. The next version will be determined in Phase 6 based on the type of changes.

### Phase 2: Get Commits Since Last Release

Using the `last_date` from above:

```bash
git log --oneline --since="<last_date>" -- . ':!.claude' ':!.erk/docs/agent' ':!.impl'
```

If `last_date` is null (no previous releases), get all commits:

```bash
git log --oneline -- . ':!.claude' ':!.erk/docs/agent' ':!.impl'
```

### Phase 3: Analyze and Categorize Commits

Group commits by type based on their messages:

**Added** (new features):

- Commits with "add", "new", "implement", "create" in message
- Feature PRs

**Changed** (improvements):

- Commits with "improve", "update", "enhance", "refactor" in message
- Non-breaking changes to existing functionality

**Fixed** (bug fixes):

- Commits with "fix", "bug", "resolve", "correct" in message
- Issue fixes

**Removed** (removals):

- Commits with "remove", "delete", "drop" in message

Filter out:

- CI/CD changes (unless they affect users)
- Documentation-only changes
- Internal refactoring
- Test-only changes
- Merge commits

### Phase 4: Draft Release Notes

Generate release notes in Keep a Changelog format:

```markdown
### Major Changes (optional, for significant user-facing features)

- Brief description of major feature and user benefit

### Added

- New feature description that explains the benefit to users

### Changed

- Description of what was improved or modified

### Fixed

- Description of what bug was fixed and the impact

### Removed

- Description of what was removed (if applicable)
```

Guidelines:

- Focus on user benefit, not implementation details
- Start with a verb (Added, Fixed, Improved)
- Be concise but clear (1 sentence each)
- Only include sections that have entries
- Use "Major Changes" for significant user-facing features (PyPI publishing, major architecture changes, new systems)

### Phase 5: User Review

Present the draft using AskUserQuestion:

**Question**: "Here are the proposed release notes. What would you like to change?"

**Options**:

1. "Approve as-is" - Use the notes without changes
2. "Edit items" - I'll modify specific entries
3. "Start over" - Let me provide manual notes

### Phase 6: Determine Next Version

Calculate the **next** version based on `current_version` and the type of changes:

- **Patch** (X.Y.Z+1): Bug fixes only
- **Minor** (X.Y+1.0): New features, no breaking changes
- **Major** (X+1.0.0): Breaking changes (rare, usually explicit)

For example, if `current_version` is 0.2.1 and changes include new features, suggest 0.2.2 (patch) or 0.3.0 (minor).

Ask user to confirm version:

**Question**: "Based on changes, the current version is X.Y.Z. Suggested next version is A.B.C. Is this correct?"

**Options**:

1. "Yes, use A.B.C"
2. "Use different version" (let user specify)

### Phase 7: Update CHANGELOG

Write the approved notes to a temporary file:

```bash
cat > /tmp/release-notes.md << 'EOF'
### Added
- Feature description...

### Fixed
- Bug fix description...
EOF
```

Then use the deterministic CLI to update CHANGELOG.md:

```bash
erk-dev release-update --version <new_version> --notes-file /tmp/release-notes.md
```

### Output Format

**Start**: "Analyzing commits for release notes..."

**Analysis**: Show commit count and categories found

**Draft**: Present formatted release notes

**After approval**: "Updated CHANGELOG.md with version X.Y.Z release notes"
