# Documentation Plan: Consolidated erk-learn Documentation Gaps

> **Consolidates:** #5914, #5913, #5910, #5909, #5901, #5898, #5895

## Context

This plan consolidates 7 open erk-learn documentation plans into a single unified effort. Each original plan emerged from implementation sessions where code was shipped but documentation was not completed. The common pattern: code implementations are complete and working, but the documentation that would help future agents avoid mistakes or understand patterns was never written.

The consolidated items focus on three areas: (1) documenting command patterns and architectural decisions that emerged from complex implementations, (2) creating tripwires for non-obvious behaviors that caused issues during implementation, and (3) updating existing docs with new examples and patterns.

## Raw Materials

Investigation comments posted to original issues:
- #5914: https://github.com/dagster-io/erk/issues/5914#issuecomment-3796154161
- #5913: https://github.com/dagster-io/erk/issues/5913#issuecomment-3796154194
- #5910: https://github.com/dagster-io/erk/issues/5910#issuecomment-3796154440
- #5909: https://github.com/dagster-io/erk/issues/5909#issuecomment-3796154466
- #5901: https://github.com/dagster-io/erk/issues/5901#issuecomment-3796155029
- #5898: https://github.com/dagster-io/erk/issues/5898#issuecomment-3796155055
- #5895: https://github.com/dagster-io/erk/issues/5895#issuecomment-3796155085

## Source Plans

| #    | Title                                              | Items Merged |
|------|----------------------------------------------------|--------------|
| 5914 | Skip --shell flag setup commands in codespace connect | 3 items |
| 5913 | Remove tripwire_candidates module                   | 6 items |
| 5910 | Phase 5 - Consolidate Confirmation Prompts in erk land | 4 items |
| 5909 | Fix Remote Implementation Creates Wrong Branch      | 3 items |
| 5901 | Add tripwire promotion steelthread for erk land     | 9 items |
| 5898 | Consolidated erk-learn Documentation Gaps           | 5 items |
| 5895 | Learn Plan: Phase 1B Worktree Gateway Migration     | 3 items |

## Summary

| Metric                         | Count |
|--------------------------------|-------|
| Documentation items            | 18    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 2     |

## Documentation Items

### HIGH Priority

#### 1. Two-Phase Validation Model for Complex Commands

**Location:** `docs/learned/cli/two-phase-validation-model.md`
**Action:** CREATE
**Source:** [Impl] from #5910

**Draft Content:**

```markdown
---
title: Two-Phase Validation Model for Complex Commands
read_when:
  - "implementing commands with multiple confirmations"
  - "designing commands that perform destructive mutations"
  - "working on erk land or similar multi-step commands"
---

# Two-Phase Validation Model

Complex CLI commands that perform multiple mutations should use a two-phase model:

## Phase 1: Validation
- Gather ALL user confirmations upfront
- Perform all precondition checks
- NO mutations occur in this phase
- Collect all decisions into confirmation objects

## Phase 2: Execution
- Perform mutations in sequence
- Use pre-gathered confirmations
- No user interaction in this phase

## Why This Matters

Partial mutations are dangerous. If a command:
1. Merges a PR
2. Asks for confirmation to delete worktree
3. User says no

The PR is already merged but the worktree remains - an inconsistent state.

## Implementation Pattern

See `CleanupConfirmation` in `land_cmd.py` for the canonical example.

## Reference Implementation

`src/erk/cli/commands/land_cmd.py` lines 107-208, 1315, 1680
```

---

#### 2. Tripwire Promotion Workflow

**Location:** `docs/learned/planning/tripwire-promotion-workflow.md`
**Action:** CREATE
**Source:** [Impl] from #5901

**Draft Content:**

```markdown
---
title: Tripwire Promotion Workflow
read_when:
  - "implementing tripwire candidate extraction"
  - "promoting tripwire candidates to frontmatter"
  - "understanding the learn-to-tripwire pipeline"
---

# Tripwire Promotion Workflow

How tripwire candidates flow from learn sessions to active tripwires.

## Pipeline Overview

1. **Session Analysis**: Agent errors/patterns identified in session
2. **Learn Plan**: Tripwire candidates described in prose
3. **Extraction**: Tripwire Extractor agent extracts structured candidates
4. **Storage**: `store-tripwire-candidates` saves to PR comment metadata
5. **Promotion**: `promote_tripwire_to_frontmatter()` adds to doc YAML

## Key Components

### TripwireCandidate Dataclass
Location: `erk_shared/github/metadata/tripwire_candidates.py`
Fields: `action`, `warning`, `target_doc_path`

### Tripwire Extractor Agent
Location: `.claude/agents/learn/tripwire-extractor.md`
Extracts candidates from learn plan markdown prose

### Promotion Function
Location: `erk_shared/learn/tripwire_promotion.py`
Function: `promote_tripwire_to_frontmatter()`
Returns: `PromotionResult` dataclass
```

---

#### 3. Remote Implementation Idempotency

**Location:** `docs/learned/planning/remote-implementation-idempotency.md`
**Action:** CREATE
**Source:** [Impl] from #5909

**Draft Content:**

```markdown
---
title: Remote Implementation Idempotency
read_when:
  - "implementing remote plan execution"
  - "debugging branch creation in remote workflows"
  - "working with worktree reuse patterns"
tripwires:
  - action: "reusing existing worktrees for remote implementation"
    warning: "Check if worktree already has a branch before creating new one. Reusing worktrees without checking causes PR orphaning."
---

# Remote Implementation Idempotency

Remote implementation must handle worktree reuse safely.

## The Bug (Fixed)

When remote implementation reused an existing worktree:
1. Old branch still existed
2. Code created a NEW branch anyway
3. Old PR became orphaned

## The Fix

Before creating a branch, check if the worktree already has one:
- If branch exists and matches plan, use it
- If branch exists but differs, error clearly
- Only create new branch if none exists

## Reference

Commit: f9807f2d
```

---

### MEDIUM Priority

#### 4. GitHub Metadata Patterns

**Location:** `docs/learned/architecture/github-metadata-patterns.md`
**Action:** CREATE
**Source:** [Impl] from #5901

**Draft Content:**

```markdown
---
title: GitHub Metadata Patterns
read_when:
  - "storing structured data in GitHub issues/PRs"
  - "implementing new metadata block types"
  - "extracting metadata from issue/PR comments"
---

# GitHub Metadata Patterns

How erk stores and retrieves structured data using GitHub issue/PR comments.

## Metadata Block Format

Metadata is stored in HTML comments within issue/PR bodies or comments:

<!-- erk:metadata-block:<block-type> -->
<details>
<summary>Metadata</summary>
... YAML or content ...