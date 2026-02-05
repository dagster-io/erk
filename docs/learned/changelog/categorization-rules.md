---
title: Changelog Categorization Rules
read_when:
  - "categorizing changelog entries"
  - "updating CHANGELOG.md"
  - "running /local:changelog-update command"
last_audited: "2026-02-05 14:23 PT"
audit_result: edited
---

# Changelog Categorization Rules

The authoritative categorization rules live in `.claude/agents/changelog/commit-categorizer.md`. When this document conflicts with the agent definition, the agent definition is correct.

This document exists as a quick-reference pointer. For the complete decision tree, exclusion patterns, commit consolidation guidelines, and confidence flags, read the agent definition directly.

## Related Documentation

- [Changelog Standards](../reference/changelog-standards.md) - Entry format and Keep a Changelog compliance
- [Agent Delegation](../planning/agent-delegation.md) - How changelog-update uses the commit-categorizer agent
