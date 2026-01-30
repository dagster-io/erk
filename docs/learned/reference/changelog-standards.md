---
title: Changelog Standards and Format
read_when:
  - "writing CHANGELOG.md entries"
  - "formatting changelog sections"
  - "understanding sync marker format"
---

# Changelog Standards and Format

CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format with erk-specific conventions for commit references and sync markers.

## Entry Format

### Standard Entry

```markdown
- {Description of change in past tense, user-focused} ({commit_hash})
```

**Examples:**

```markdown
- Fix discover-reviews for large PRs by switching to REST API with pagination (ab3ff4e58)
- Consolidate `erk init capability list` and `erk init capability check` into unified command (57a406f39)
```

### Multiple Commits (Single Feature)

When a feature spans multiple commits, reference all relevant hashes:

```markdown
- {Description of complete feature} ({hash1}, {hash2}, {hash3})
```

**Example:**

```markdown
- Add plan review via temporary PR workflow (03b9e3a9d, 260f8a059, 46a916ddb, 436045eee)
```

### Large Features (Major Changes)

Major Changes use a different format with explanatory prose:

```markdown
- **Feature Name**: Brief description. Motivation/problem statement. Value to user. ({primary_hash}, {supporting_hash1}, {supporting_hash2})
```

**Example:**

```markdown
- **Plan Review via Temporary PR**: New workflow for asynchronous plan review through draft PRs. Plans can be submitted as temporary PRs for review, with feedback incorporated back into the plan issue. Includes automatic branch management, PR lifecycle handling, and integration with `/erk:pr-address`. (03b9e3a9d, 260f8a059, 46a916ddb, 436045eee, df3bda1a2, 90887e08b, 8f7b8811d, 8c7c66480, 712fffabf, f1c6fcb08, 91c06aaba)
```

**Key elements:**

1. **Bold feature name** - Short, memorable name
2. **What it does** - Brief functional description
3. **Motivation** - Why we built it, what problem it solves
4. **Value** - What benefit users get
5. **All commit hashes** - Primary commit first, then supporting commits

## Keep a Changelog Compliance

### User Focus

**Good (user-focused):**

- "Fix discover-reviews for large PRs by switching to REST API with pagination"
- "Auto-fix Graphite tracking divergence in sync and branch creation"

**Bad (implementation-focused):**

- "Refactor discover-reviews to use REST API instead of GraphQL"
- "Add tracking divergence detection logic to sync command"

### Past Tense

**Good:**

- "Added plan review workflow"
- "Fixed detached HEAD state"
- "Removed fallback indicator"

**Bad:**

- "Add plan review workflow"
- "Fix detached HEAD state"
- "Remove fallback indicator"

### Logical Grouping

Group related entries together within a category:

```markdown
### Changed

- Move code reviews to Haiku model with flag-only prompts (67bd9922e)
- Fix discover-reviews for large PRs by switching to REST API (ab3ff4e58)
- Auto-fix Graphite tracking divergence (8b8b06b53)
```

Not scattered randomly based on commit order.

## Commit Reference Formats

### Single Commit

Short hash (9 characters):

```markdown
({commit_hash})
```

Example: `(ab3ff4e58)`

### Multiple Commits

Comma-separated, space after each comma:

```markdown
({hash1}, {hash2}, {hash3})
```

Example: `(03b9e3a9d, 260f8a059, 46a916ddb)`

### Many Commits (10+)

For very large features with 10+ commits, consider:

1. **Roll-up entry** - Consolidate into single entry with all hashes
2. **Primary only** - Reference only the primary commit if supporting commits are minor fixes

## Sync Marker Format

The "As of" marker tracks the last commit included in CHANGELOG.md:

```markdown
<!-- As of: `{commit_hash}` -->
```

**Placement:** First line of the `## [Unreleased]` section, after the section header.

**Example:**

```markdown
## [Unreleased]

<!-- As of: `03b9e3a9d` -->

### Major Changes
```

### Marker Lifecycle

1. **Parsing** - `erk-dev changelog-commits` reads the marker to find the starting point
2. **Querying** - `git log {marker_hash}..HEAD --first-parent` gets new commits
3. **Updating** - After adding entries, marker is updated to current HEAD

**Commands:**

```bash
# Get commits since marker
erk-dev changelog-commits --json-output

# Update marker to current HEAD
erk-dev changelog-update-marker
```

### Missing Marker

If no marker exists (new repo or marker accidentally deleted):

1. Find the most recent release version in CHANGELOG.md (e.g., `## [0.7.0]`)
2. Find the release commit: `git log --oneline -1 --grep="0.7.0"`
3. Get commits since that release: `erk-dev changelog-commits --since {release_hash} --json-output`

## Section Order

Sections appear in this order (omit empty sections):

1. Major Changes
2. Added
3. Changed
4. Fixed
5. Removed

**Example:**

```markdown
## [Unreleased]

<!-- As of: `{hash}` -->

### Major Changes

- ...

### Added

- ...

### Fixed

- ...
```

(No "Changed" or "Removed" sections if they're empty)

## Release Section Format

When cutting a release:

```markdown
## [{version}] - {date} {time} {timezone}

### Release Overview

{High-level summary of what's in this release}
```

**Example:**

```markdown
## [0.7.0] - 2026-01-24 15:12 PT

### Release Overview

This release adds remote execution capabilities, plan replanning workflows, and numerous TUI improvements for managing plans and PRs.
```

## Related Documentation

- [Categorization Rules](../changelog/categorization-rules.md) - How to categorize commits
- [Agent Delegation](../planning/agent-delegation.md) - changelog-update workflow
