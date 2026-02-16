---
title: Changelog Standards and Format
read_when:
  - "writing CHANGELOG.md entries manually"
  - "understanding the changelog sync marker system"
  - "deciding how to format a changelog entry"
tripwires:
  - action: "adding a changelog entry without a commit hash reference"
    warning: "All unreleased entries must include 9-character short hashes in parentheses. Hashes are stripped at release time by /local:changelog-release."
  - action: "writing implementation-focused changelog entries"
    warning: "Entries must describe user-visible behavior, not internal implementation. Ask: 'Does an erk user see different behavior?'"
  - action: "modifying CHANGELOG.md directly instead of using /local:changelog-update"
    warning: "Always use /local:changelog-update to sync with commits. Manual edits bypass the categorization agent and marker system."
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# Changelog Standards and Format

CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with erk-specific conventions. This document explains the design decisions behind the format — for the authoritative entry format and workflow steps, see the command files linked below.

## System Architecture

The changelog system has three components that must stay coordinated:

| Component                  | Role                                        | Authority over                                          |
| -------------------------- | ------------------------------------------- | ------------------------------------------------------- |
| `/local:changelog-update`  | Syncs unreleased section with new commits   | Update workflow, entry format, marker management        |
| `/local:changelog-release` | Finalizes unreleased into versioned section | Release format, hash stripping, version bumping         |
| Commit categorizer agent   | Classifies commits into categories          | Category assignment, filtering rules, roll-up detection |

<!-- Source: .claude/commands/local/changelog-update.md -->
<!-- Source: .claude/commands/local/changelog-release.md -->
<!-- Source: .claude/agents/changelog/commit-categorizer.md -->

The update command orchestrates the categorizer agent, presents a proposal for human review, and only writes to CHANGELOG.md after approval. The release command transforms the unreleased section into a versioned one. See each command file for workflow details.

## Entry Format Reference

### Standard Entry

```markdown
- {Imperative verb} {description of change, user-focused} ({commit_hash})
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

## Why Commit Hash References Exist

Unreleased entries include 9-character short hashes (e.g., `(ab3ff4e58)`) for traceability during review. When a human reviews the changelog proposal, they can quickly `git show` any hash to verify the entry accurately represents the change.

At release time, `/local:changelog-release` strips all hashes. Released entries stand alone without implementation references — they describe user-visible outcomes, not code history.

This two-phase lifecycle is why hashes appear in unreleased entries but not in versioned sections of `CHANGELOG.md`.

### Commit Reference Formats

Hashes are 9-character short hashes in parentheses: `(ab3ff4e58)`. Multiple commits use comma-separated format: `(03b9e3a9d, 260f8a059, 46a916ddb)`. See the entry format examples above for full context.

For very large features with 10+ commits, consider:

1. **Roll-up entry** - Consolidate into single entry with all hashes
2. **Primary only** - Reference only the primary commit if supporting commits are minor fixes

## The Sync Marker System

The "As of" marker in the Unreleased section is a cursor — it tells `erk-dev changelog-commits` where to start scanning for new commits. The marker uses `git log {marker}..HEAD --first-parent` to find only mainline commits, excluding feature branch history.

### Sync Marker Format

The parser (`parse_changelog_marker` in `packages/erk-dev/src/erk_dev/commands/changelog_commits/command.py`) accepts two formats:

1. **Backtick format** (visible in rendered markdown): `` As of `{commit_hash}` ``
2. **HTML comment format** (invisible in rendered markdown): `<!-- As of {commit_hash} -->`

**Placement:** First line of the `## [Unreleased]` section, after the section header.

**Example:**

```markdown
## [Unreleased]

<!-- As of 03b9e3a9d -->

### Major Changes
```

### Marker Lifecycle

1. **Parsing** - `erk-dev changelog-commits` reads the marker to find the starting point
2. **Querying** - `git log {marker_hash}..HEAD --first-parent` gets new commits
3. **Updating** - After adding entries, marker is updated to current HEAD

**Why `--first-parent`:** Without it, squash-merged PRs would expose individual feature branch commits that are already consolidated into the squash commit's entry.

### Missing Marker Recovery

If the marker is accidentally deleted, `erk-dev changelog-commits` has a built-in fallback: it parses the most recent release version from CHANGELOG.md and resolves the corresponding git tag to find the starting commit. The categorizer agent can also use `--since` to specify a commit directly.

The fallback path in `changelog_commits/command.py`:

1. `parse_last_release_version()` finds the first version header after `[Unreleased]` (e.g., `0.7.0`)
2. `get_release_tag_commit()` resolves the git tag `v{version}` via `git rev-parse --verify v0.7.0^{commit}`
3. Uses that tag commit as the marker, same as normal flow

The categorizer agent can also bypass marker parsing entirely: `erk-dev changelog-commits --since {release_hash} --json-output`

## Entry Writing Decisions

### User-Visible Framing

The hardest judgment call in changelog writing is framing. The same change can be described from the implementation side or the user side.

**WRONG** (implementation-focused): "Refactor discover-reviews to use REST API instead of GraphQL"
**RIGHT** (user-focused): "Fix discover-reviews for large PRs by switching to REST API with pagination"

More examples:

**Good (user-focused):**

- "Fix discover-reviews for large PRs by switching to REST API with pagination"
- "Auto-fix Graphite tracking divergence in sync and branch creation"

**Bad (implementation-focused):**

- "Refactor discover-reviews to use REST API instead of GraphQL"
- "Add tracking divergence detection logic to sync command"

The test: describe the **problem solved or behavior changed**, not the technical approach. The implementation is available via the commit hash.

### Imperative Verb Convention

Entries use imperative mood verbs (matching `/local:changelog-update` which instructs "Start with a verb: Add, Fix, Improve, Remove, Move, Migrate"):

**Good:**

- "Add plan review workflow"
- "Fix detached HEAD state"
- "Remove fallback indicator"

**Bad:**

- "Added plan review workflow"
- "Fixed detached HEAD state"
- "Removed fallback indicator"

### When Entries Become Major Changes

Regular entries are single-line items under Added/Changed/Fixed/Removed. Major Changes use a different structure: bold feature name, explanatory prose covering what/why/value, and consolidated commit hashes.

The threshold is not code size — it's **conceptual significance**. A feature that changes how users think about the tool (e.g., "Plan Review via Temporary PR") is a Major Change. A large refactor that users never notice is filtered entirely.

See `CHANGELOG.md` for living examples of both formats.

### Roll-Up vs Separate Entries

Multiple commits implementing a single feature should consolidate into one entry. This prevents the changelog from reading like a git log. The categorizer agent detects roll-up candidates by keyword clustering and sequential PR numbers.

The presentation should describe the **complete feature**, not the implementation journey. Five commits about "artifact sync" become one entry explaining what artifact sync does for users.

## Section Ordering

Categories follow a fixed order: Major Changes, Added, Changed, Fixed, Removed. Empty categories are omitted entirely — don't include empty headers. This order puts the most significant changes first.

**Example:**

```markdown
## [Unreleased]

<!-- As of {hash} -->

### Major Changes

- ...

### Added

- ...

### Fixed

- ...
```

(No "Changed" or "Removed" sections if they're empty)

## Release Workflow Decisions

### Release Section Header Format

```markdown
## [{version}] - {date} {time} {timezone}
```

**Example:**

```markdown
## [0.7.0] - 2026-01-24 15:12 PT

### Release Overview

This release adds remote execution capabilities, plan replanning workflows, and numerous TUI improvements for managing plans and PRs.
```

### Minor vs Patch Releases

<!-- Source: .claude/commands/local/changelog-release.md, Phase 3 -->

Patch releases (X.Y.Z+1) are the default. Minor releases (X.Y+1.0) add a **Release Overview** section that consolidates themes across the preceding patch series. The decision to cut a minor release is always human-driven — the release command prompts for it.

### Release Overview Structure

Minor releases include narrative theme sections (What it solves / How it works / Key features) that provide context beyond the individual entries. These themes span multiple patch releases and describe the arc of development, not just individual changes.

See the `[0.7.0]` and `[0.7.1]` sections in `CHANGELOG.md` for living examples of both release formats.

## Related Documentation

- [Categorization Rules](../changelog/categorization-rules.md) — why-level rationale for category assignment and filtering decisions
- [Agent Delegation](../planning/agent-delegation.md) — how changelog-update orchestrates the commit-categorizer agent
