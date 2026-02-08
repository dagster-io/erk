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
last_audited: "2026-02-08"
audit_result: edited
---

# Changelog Standards and Format

CHANGELOG.md follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with erk-specific conventions. This document explains the design decisions behind the format — for the authoritative entry format and workflow steps, see the command files linked below.

## System Architecture

The changelog system has three components that must stay coordinated:

| Component | Role | Authority over |
|-----------|------|---------------|
| `/local:changelog-update` | Syncs unreleased section with new commits | Update workflow, entry format, marker management |
| `/local:changelog-release` | Finalizes unreleased into versioned section | Release format, hash stripping, version bumping |
| Commit categorizer agent | Classifies commits into categories | Category assignment, filtering rules, roll-up detection |

<!-- Source: .claude/commands/local/changelog-update.md -->
<!-- Source: .claude/commands/local/changelog-release.md -->
<!-- Source: .claude/agents/changelog/commit-categorizer.md -->

The update command orchestrates the categorizer agent, presents a proposal for human review, and only writes to CHANGELOG.md after approval. The release command transforms the unreleased section into a versioned one. See each command file for workflow details.

## Why Commit Hash References Exist

Unreleased entries include 9-character short hashes (e.g., `(ab3ff4e58)`) for traceability during review. When a human reviews the changelog proposal, they can quickly `git show` any hash to verify the entry accurately represents the change.

At release time, `/local:changelog-release` strips all hashes. Released entries stand alone without implementation references — they describe user-visible outcomes, not code history.

This two-phase lifecycle is why hashes appear in unreleased entries but not in versioned sections of `CHANGELOG.md`.

## The Sync Marker System

The `<!-- As of: ... -->` HTML comment in the Unreleased section is a cursor — it tells `erk-dev changelog-commits` where to start scanning for new commits. The marker uses `git log {marker}..HEAD --first-parent` to find only mainline commits, excluding feature branch history.

**Why `--first-parent`:** Without it, squash-merged PRs would expose individual feature branch commits that are already consolidated into the squash commit's entry.

**Missing marker recovery:** If the marker is accidentally deleted, the categorizer agent falls back to finding the last release version header and using `--since` to specify a commit directly. This is documented in the categorizer agent's error handling.

## Entry Writing Decisions

### User-Visible Framing

The hardest judgment call in changelog writing is framing. The same change can be described from the implementation side or the user side.

**WRONG** (implementation-focused): "Refactor discover-reviews to use REST API instead of GraphQL"
**RIGHT** (user-focused): "Fix discover-reviews for large PRs by switching to REST API with pagination"

The test: describe the **problem solved or behavior changed**, not the technical approach. The implementation is available via the commit hash.

### When Entries Become Major Changes

Regular entries are single-line items under Added/Changed/Fixed/Removed. Major Changes use a different structure: bold feature name, explanatory prose covering what/why/value, and consolidated commit hashes.

The threshold is not code size — it's **conceptual significance**. A feature that changes how users think about the tool (e.g., "Plan Review via Temporary PR") is a Major Change. A large refactor that users never notice is filtered entirely.

See `CHANGELOG.md` for living examples of both formats.

### Roll-Up vs Separate Entries

Multiple commits implementing a single feature should consolidate into one entry. This prevents the changelog from reading like a git log. The categorizer agent detects roll-up candidates by keyword clustering and sequential PR numbers.

The presentation should describe the **complete feature**, not the implementation journey. Five commits about "artifact sync" become one entry explaining what artifact sync does for users.

## Section Ordering

Categories follow a fixed order: Major Changes, Added, Changed, Fixed, Removed. Empty categories are omitted entirely — don't include empty headers. This order puts the most significant changes first.

## Release Workflow Decisions

### Minor vs Patch Releases

<!-- Source: .claude/commands/local/changelog-release.md, Phase 3 -->

Patch releases (X.Y.Z+1) are the default. Minor releases (X.Y+1.0) add a **Release Overview** section that consolidates themes across the preceding patch series. The decision to cut a minor release is always human-driven — the release command prompts for it.

### Release Overview Structure

Minor releases include narrative theme sections (What it solves / How it works / Key features) that provide context beyond the individual entries. These themes span multiple patch releases and describe the arc of development, not just individual changes.

See the `[0.7.0]` and `[0.7.1]` sections in `CHANGELOG.md` for living examples of both release formats.

## Related Documentation

- [Categorization Rules](../changelog/categorization-rules.md) — why-level rationale for category assignment and filtering decisions
- [Agent Delegation](../planning/agent-delegation.md) — how changelog-update orchestrates the commit-categorizer agent
