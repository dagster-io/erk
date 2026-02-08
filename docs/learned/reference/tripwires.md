---
title: Reference Tripwires
read_when:
  - "working on reference code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from reference/*.md frontmatter -->

# Reference Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding a changelog entry without a commit hash reference** → Read [Changelog Standards and Format](changelog-standards.md) first. All unreleased entries must include 9-character short hashes in parentheses. Hashes are stripped at release time by /local:changelog-release.

**CRITICAL: Before adding a new roadmap status value** → Read [Objective Summary Format](objective-summary-format.md) first. Status inference lives in two places that must stay synchronized: the roadmap parser (objective_roadmap_shared.py) and the agent prompt in objective-next-plan.md. Update both or the formats will diverge.

**CRITICAL: Before defining the same skill or command in multiple TOML sections** → Read [TOML File Handling](toml-handling.md) first. TOML duplicate key constraint: Each skill/command must have a single canonical destination. See bundled-artifacts.md for portability classification.

**CRITICAL: Before modifying CHANGELOG.md directly instead of using /local:changelog-update** → Read [Changelog Standards and Format](changelog-standards.md) first. Always use /local:changelog-update to sync with commits. Manual edits bypass the categorization agent and marker system.

**CRITICAL: Before writing implementation-focused changelog entries** → Read [Changelog Standards and Format](changelog-standards.md) first. Entries must describe user-visible behavior, not internal implementation. Ask: 'Does an erk user see different behavior?'
