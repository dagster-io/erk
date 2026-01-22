---
title: Cross-Artifact Analysis
read_when:
  - "detecting PR and plan relationships"
  - "assessing if work supersedes a plan"
  - "analyzing overlap between artifacts"
---

# Cross-Artifact Analysis

This document describes how erk commands analyze relationships between different GitHub artifacts (PRs, plans, branches, issues).

## PR-Plan Relationships

Plans and PRs can have complex relationships:

| Relationship   | Description                                         | Detection Method                              |
| -------------- | --------------------------------------------------- | --------------------------------------------- |
| Linked         | PR explicitly references plan issue                 | PR body contains `Plan: #<issue>` reference   |
| Superseding    | PR implements work that makes plan obsolete         | Compare PR changes with plan intent           |
| Partial        | PR implements subset of plan scope                  | Evidence-based analysis of overlap            |
| Independent    | PR and plan address unrelated concerns              | No meaningful overlap in changes              |

## Evidence-Based Analysis Pattern

The `/local:check-relevance` command implements a structured approach to cross-artifact analysis:

1. **Parse input** - Identify whether target is PR or plan
2. **Gather context** - Retrieve GitHub metadata and plan content
3. **Understand intent** - Extract what changes were planned
4. **Search for evidence** - Check master branch for matching implementations
5. **Create evidence table** - Document findings with specific file/function matches
6. **Determine verdict** - Apply classification thresholds

This pattern can be adapted for future commands that need to assess relationships between artifacts.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Plan states and verdict classifications
- [Local Command Patterns](../cli/local-commands.md) - Command taxonomy
