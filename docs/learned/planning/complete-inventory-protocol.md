---
title: Complete File Inventory Protocol
read_when:
  - "estimating effort or remaining work for a plan or PR"
  - "closing a plan issue as complete"
  - "creating a consolidation plan from multiple PRs"
tripwires:
  - action: "estimating effort for a plan without checking actual files changed"
    warning: "Run a file inventory first. Plans that skip inventory systematically undercount configuration, test, and documentation changes."
  - action: "closing a plan issue without verifying all items were addressed"
    warning: "Compare the file inventory against the plan's items before closing. Silent omissions are the most common failure mode."
---

# Complete File Inventory Protocol

## Why This Matters

Agents systematically underestimate work when they reason only from plan text without checking what actually changed. The gap between "what the plan describes" and "what the PR touches" consistently falls into the same blind spots:

- **Configuration changes** (settings.json, pyproject.toml, CI workflows) that accompany code changes but aren't mentioned in plans
- **Generated files** (index files, tripwires files) that need regeneration after structural changes
- **Test files** that need updating alongside source changes
- **Documentation files** that need creation or updates

These aren't edge cases — they're the norm. A plan that says "add a new gateway" implies 5+ files (abc, real, fake, tests, init), but agents counting from plan text alone often miss 1-2 of them.

## When to Inventory

| Situation                                              | Why                                                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Before creating a consolidation plan from multiple PRs | Each PR may have touched files the others didn't — the union is larger than any individual PR suggests |
| Before estimating remaining work on a partial plan     | Completed work may have introduced files not in the original plan                                      |
| Before closing a plan issue as "complete"              | The only reliable completion check is comparing actual files against planned items                     |
| Before scoping a replan                                | Understanding what already shipped prevents duplicate work items                                       |

## The Comparison Step

The inventory itself is trivial (a `gh pr view --json files` or `git diff --name-only`). The high-value step is **comparing the inventory against the plan's items**. Walk through the file list and ask for each file: "Is this accounted for in the plan?" Unaccounted files are either:

1. **Legitimate additions** the plan didn't anticipate — add them to the effort estimate
2. **Generated/derived files** that don't need separate effort — note but don't count
3. **Scope creep** that should be split into a separate plan

## Anti-Patterns

**Estimating from plan text alone**: An agent reads the plan's "Implementation Steps" section and counts steps. This misses all implicit work (config, tests, docs, generated files). Always check actual files.

**Trusting PR file count as effort count**: A PR touching 20 files isn't necessarily 20 units of work — some files are mechanical (import updates, re-exports). Categorize files before estimating.

**Closing a plan without diff comparison**: The plan says "done" but 2 of 8 items were silently skipped. The only way to catch this is comparing the plan's checklist against the actual diff.

## Related Documentation

- [PR Analysis Pattern](pr-analysis-pattern.md) — metadata-first approach to understanding PR changes (Step 1 uses file-level inventory)
- [Plan Lifecycle](lifecycle.md) — full plan lifecycle including relevance assessment before closing
- [Cross-Artifact Analysis](cross-artifact-analysis.md) — detecting overlap between PRs and plans
