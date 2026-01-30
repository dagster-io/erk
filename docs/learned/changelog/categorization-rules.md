---
title: Changelog Categorization Rules
read_when:
  - "categorizing changelog entries"
  - "updating CHANGELOG.md"
  - "running /local:changelog-update command"
---

# Changelog Categorization Rules

How to categorize commits into CHANGELOG.md categories and what to filter out.

## Category Hierarchy

Commits are categorized into these sections (in order of precedence):

1. **Major Changes** - Significant features or breaking changes that warrant special attention
2. **Added** - New features
3. **Changed** - Improvements to existing features
4. **Fixed** - Bug fixes
5. **Removed** - Removals or deprecations

## Decision Tree

### Major Changes

**Test:** "Does an end user running `erk` commands see significantly different behavior?"

**Include:**
- New user-facing systems or major capabilities
- Breaking changes that users need to know about
- CLI command reorganization or removal
- Features that warrant special attention in release notes

**Exclude (NEVER Major Changes):**
- Internal architecture improvements
- Gateway refactoring
- Retry mechanisms
- Schema-driven config
- Infrastructure changes invisible to users

**Entry Requirements:**

Every Major Change entry must include:

1. **What it does** - Brief description of the feature/change
2. **Motivation/purpose** - Why we built it, the problem it solves
3. **Value to user** - What benefit users get from this

**Format:**

```markdown
- **Feature name**: Brief description of what it does. Motivation explaining why we built it. Value statement about user benefit. (primary_commit_hash)
```

**Important:** Roll up all related commits (fixes, aliases, extensions) into a single entry with explanatory prose. Don't list implementation details separately.

### Added

**Detection patterns:**
- Commit message contains "add", "new", "implement", "create"
- Feature PRs introducing new functionality

**Test:** Is this a wholly new feature that didn't exist before?

**Examples:**
- New CLI commands
- New slash commands (except `/local:*` - see exclusions)
- New user-facing capabilities

### Changed

**Detection patterns:**
- Commit message contains "improve", "update", "enhance", "move", "migrate"
- Non-breaking changes to existing functionality

**Test:** Does this modify how an existing feature works without removing it?

**Examples:**
- Performance improvements
- UI/UX enhancements
- Output format improvements

### Fixed

**Detection patterns:**
- Commit message contains "fix", "bug", "resolve", "correct"
- Issue fixes

**Test:** Does this repair broken behavior?

**Examples:**
- Bug fixes
- Error handling improvements
- Edge case corrections

### Removed

**Detection patterns:**
- Commit message contains "remove", "delete", "drop"

**Test:** Is functionality being taken away?

**Examples:**
- Deprecated command removal
- Feature sunset
- API cleanup

## Exclusion Patterns

### Always Filter (never include in CHANGELOG)

**Local-only commands:**
- ANY commit adding or modifying `.claude/commands/local/*` files
- These are developer-only commands not shipped to users
- Filter even if message sounds like a new feature (e.g., "Add /local:foo command")

**Release housekeeping:**
- Version bumps ("Bump version to X")
- CHANGELOG finalization
- Lock file updates for releases

**CI/CD-only changes:**
- `.github/workflows/` changes (unless capability-related, see exception below)

**Documentation-only:**
- `docs/`, `.md` files in `.erk/`
- Skill/agent documentation updates

**Test-only:**
- Changes only in `tests/`

**Internal code conventions:**
- Frozen dataclasses migrations
- Parameter default removal
- Import reorganization

**Gateway method additions:**
- `abc.py`, `real.py`, `fake.py`, `dry_run.py`, `printing.py` pattern
- Pure plumbing with no user-visible behavior

**Build tooling:**
- `Makefile`, `pyproject.toml` dependency updates

**Merge commits:**
- Commits with no substantive changes

**Vague messages:**
- "update", "WIP", "wip" with no context

**Internal abstractions:**
- Consolidation of internal types (e.g., Terminal+UserFeedback->Console)
- Refactoring with no user-visible change

**erk-dev commands:**
- All changes to `erk-dev` tooling
- Internal development utilities

**erk exec commands:**
- ALL changes to `src/erk/cli/commands/exec/scripts/`
- These are internal tooling, always filter

### Exception: Capability Workflows ARE External-Facing

Changes to `.github/workflows/` that affect capabilities (e.g., `dignified-python-review.yml`) ARE user-facing and should be included, since capabilities are user-installable features.

### Likely Internal (verify before including)

**Commit message keywords that often indicate internal-only:**
- "Refactor", "Relocate", "Consolidate" - check if user-visible
- "Harden", "Strengthen" - usually internal enforcement

**Path-based signals:**
- Changes only in `tests/` -> internal
- Changes only in `scripts/` (unless CLI-facing) -> internal
- Changes only to `**/fake*.py` -> internal
- Changes only to `Makefile` -> internal

### Abstraction Consolidation Pattern

When internal abstractions are merged, consolidated, or refactored, filter them out even if many files change.

**The test:** Does an end user calling `erk` commands see different behavior? If no, filter it.

**Examples (always filter):**
- "Consolidate X and Y into Z" where X, Y, Z are internal types
- "Unify X gateway" where the gateway interface is internal
- "Merge X module into Y" for internal modules

## Commit Consolidation Guidelines

### Roll-Up Detection

When multiple commits are part of a larger initiative, group them under a single Major Change entry.

**Detection patterns:**
- Multiple commits mentioning same keyword (e.g., "kit", "artifact", "hook")
- Commits with sequential PR numbers on same topic
- Commits referencing same GitHub issue/objective

**Examples:**
- 5+ commits about "kit" removal -> "Eliminate kit infrastructure entirely"
- 3+ commits about "artifact sync" -> "Add unified artifact distribution system"

**Presentation:** Roll up all related commits into one entry with explanatory prose. Include primary commit hash. Don't list each incremental commit separately.

### Multi-Commit Features

When a feature spans multiple commits (initial implementation + follow-up fixes/improvements):

1. **Identify the primary commit** - Usually the first commit introducing the feature
2. **Roll up follow-ups** - Include fixes, aliases, extensions in the same entry
3. **Single narrative** - Write one coherent entry explaining the complete feature
4. **Primary hash only** - Reference only the main commit hash

## Confidence Flags

Mark entries as **low-confidence** when:

- Commit message is ambiguous (e.g., "update X" could be Changed or internal)
- Scope is unclear (could be user-facing or internal-only)
- Category is borderline (e.g., "Add X" but it's really a refactor)
- Large architectural changes that might or might not affect users
- Commits that touch both user-facing and internal code

Low-confidence entries require human review before inclusion.

## Authoritative Source

The authoritative categorization rules live in `.claude/agents/changelog/commit-categorizer.md`.

When this document conflicts with the agent definition, the agent definition is correct.

## Related Documentation

- [Changelog Standards](../reference/changelog-standards.md) - Entry format and Keep a Changelog compliance
- [Agent Delegation](../planning/agent-delegation.md) - How changelog-update uses the commit-categorizer agent
