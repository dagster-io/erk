---
audit_result: clean
tripwires:
  - action: "categorizing internal refactors in changelog"
    warning: "NEVER categorize internal refactors as Major Changes—they must be user-visible"
  - action: "including .claude/commands/local/* changes in changelog"
    warning: "ALWAYS filter .claude/commands/local/* changes (developer-only)"
  - action: "writing changelog entries"
    warning: "NEVER expose implementation details in changelog entries"
---

# Changelog Categorization Rules

<!-- Source: .claude/agents/changelog/commit-categorizer.md -->

The authoritative categorization decision tree lives in `.claude/agents/changelog/commit-categorizer.md`. This document explains WHY the rules exist and the cross-cutting principles that inform categorization.

## Philosophy: User-Visible Behavior is the Only Signal

The central tension in changelog categorization: agents see all code changes and want to document everything. The discipline: **only user-visible behavior earns a changelog entry**.

### The User-Visibility Test

Ask: "Does someone running `erk` commands see different behavior?"

- **YES** → Changelog entry (maybe)
- **NO** → Filter out (always)

This test prevents internal architecture improvements, gateway refactoring, retry mechanisms, schema-driven config, and infrastructure changes from polluting the changelog. These are implementation details invisible to users.

### Why This Matters

Changelogs that mix internal refactors with user-facing changes become noise. Users scanning for "what changed?" don't care about gateway ABC additions or frozen dataclass migrations. They care about new commands, bug fixes, and behavior changes.

**The cost of noise:** Users stop reading changelogs. When every internal refactor gets an entry, the signal drowns in implementation trivia.

## Major Changes: The Higher Bar

<!-- Source: .claude/agents/changelog/commit-categorizer.md, Major Changes section -->

Major Changes have a stricter test: not just user-visible, but **significantly** user-visible. The kind of change users should know about before upgrading.

### What Qualifies as Major

- New user-facing systems (e.g., plan review workflow)
- Breaking changes requiring workflow adjustments
- CLI command reorganization or removal
- Features that change how users think about the tool

### What Doesn't Qualify

Even if user-visible, these are NOT Major Changes:

- Bug fixes (goes in Fixed)
- Small feature additions (goes in Added)
- Performance improvements invisible to workflow (filter entirely)
- Internal architecture improvements (filter entirely)

**Anti-pattern:** "Add retry mechanism to git operations" → This is infrastructure. Filter it. Users don't care that git calls now retry.

**Correct:** "Fix intermittent git push failures in multi-worktree environments" → This describes the user-visible problem that was fixed.

## The Local Commands Exception

<!-- Source: .claude/agents/changelog/commit-categorizer.md, Filter Out section -->

All changes to `.claude/commands/local/*` are filtered. **Always.** Even if the commit message says "Add major new feature."

**Why:** Local commands are developer-only tooling for erk contributors. They're not shipped to users. Including them in the changelog is a category error.

**Detection pattern:** Any commit touching paths matching `.claude/commands/local/*.md` gets filtered.

## Roll-Up: Merging Related Commits

<!-- Source: .claude/agents/changelog/commit-categorizer.md, Roll-Up Detection section -->

Multiple commits implementing a single feature should consolidate into one entry. This prevents changelog bloat and provides narrative cohesion.

### Detection Signals

- Multiple commits mentioning same keyword (e.g., "kit", "artifact sync")
- Sequential PR numbers on same topic
- Commits referencing same GitHub issue/objective

### Presentation Strategy

Don't list implementation commits separately. Merge them into explanatory prose:

**Bad (commit-by-commit):**

- Add artifact sync command (abc123)
- Fix artifact sync edge case (def456)
- Add artifact sync alias (ghi789)

**Good (rolled up):**

- **Artifact Sync**: Unified artifact distribution system. Enables sharing Claude Code capabilities across worktrees. Supports aliasing and handles edge cases in multi-worktree scenarios. (abc123, def456, ghi789)

The roll-up communicates the complete feature, not the implementation journey.

## Confidence Flags: Admitting Uncertainty

<!-- Source: .claude/agents/changelog/commit-categorizer.md, Confidence Flags section -->

Mark entries as **low-confidence** when categorization is ambiguous. This signals to the human reviewer: "I'm guessing, please verify."

### When to Flag

- Commit message is vague ("update X" could be Changed or internal)
- Scope is unclear (could be user-facing or internal-only)
- Large architectural changes that might affect users
- Commits touching both user-facing and internal code

**Why this matters:** Agents shouldn't pretend certainty when they're uncertain. The human has context the agent lacks. Flag the ambiguity explicitly.

## The erk-exec Exception

<!-- Source: .claude/agents/changelog/commit-categorizer.md, Filter Out section -->

All changes to `src/erk/cli/commands/exec/scripts/` are filtered. These are internal tooling for erk workflows, not user-facing commands.

**Why:** The `erk exec` namespace is internal infrastructure. Users don't invoke these scripts directly. They're called by slash commands and workflows.

## Source of Truth

For the complete decision tree, category definitions, and filtering patterns, see `.claude/agents/changelog/commit-categorizer.md`. That agent definition is executable and maintained. This document explains the rationale behind the rules.

## Related Documentation

- [Changelog Standards](../reference/changelog-standards.md) - Entry format and Keep a Changelog compliance
- [Agent Delegation](../planning/agent-delegation.md) - How changelog-update uses the commit-categorizer agent
