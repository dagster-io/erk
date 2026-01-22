# Documentation Plan: Create /local:check-relevance command for assessing PR and plan relevance

## Context

This implementation introduced `/local:check-relevance`, a new Claude Code local command that helps developers quickly assess whether a PR or plan's intended work is already represented in the master branch. The command provides a focused, single-item assessment capability that complements the existing batch audit commands (`/local:audit-branches` and `/local:audit-plans`).

The implementation establishes a new pattern in erk's local command taxonomy: **single-item assessment commands**. Unlike batch audit commands that scan the entire repository and categorize multiple items, `/local:check-relevance` operates on one specific PR or plan at a time, providing detailed evidence-based analysis inline during development workflows. This distinction is valuable for future command designers to understand.

The command introduces a structured 5-category verdict classification system (SUPERSEDED, PARTIALLY_IMPLEMENTED, DIFFERENT_APPROACH, STILL_RELEVANT, NEEDS_REVIEW) that provides consistent language for evaluating the relationship between planned work and existing code. This classification system should be referenced by future commands that need to assess similar relationships to maintain consistency across the erk tooling ecosystem.

## Raw Materials

https://gist.github.com/schrockn/5089906ca2f0ac8ab0a4a1acc83223e9

## Summary

| Metric                    | Count |
| ------------------------- | ----- |
| Documentation items       | 5     |
| Contradictions to resolve | 0     |
| Tripwires to add          | 1     |

## Documentation Items

### HIGH Priority

#### 1. Add cross-references to `/audit-branches.md` for single-item assessment

**Location:** `.claude/commands/local/audit-branches.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Related Commands

For assessing a single PR or plan's relevance (faster than a full audit), use:

```bash
/local:check-relevance <issue-number>
```

This provides focused, inline assessment during development workflows when you need to quickly determine if specific work is already implemented.
```

---

#### 2. Add cross-references to `/audit-plans.md` for single-item assessment

**Location:** `.claude/commands/local/audit-plans.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Related Commands

For assessing a single plan's relevance without running a full audit, use:

```bash
/local:check-relevance <issue-number>
```

This provides focused, evidence-based assessment inline when reviewing or creating plans.
```

---

### MEDIUM Priority

#### 1. Document single-item vs batch audit command pattern

**Location:** `docs/learned/cli/local-commands.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Local Command Patterns
read_when:
  - "designing local commands"
  - "understanding local command taxonomy"
  - "creating audit or assessment commands"
---

# Local Command Patterns

Local commands (`.claude/commands/local/`) are agent instruction files that extend Claude Code with project-specific capabilities. This document describes the patterns and taxonomy for erk local commands.

## Command Categories

### Batch Audit Commands

Batch audit commands scan the repository comprehensively and categorize multiple items:

| Command             | Scope              | Purpose                              |
| ------------------- | ------------------ | ------------------------------------ |
| `/audit-branches`   | All branches/PRs   | Identify stale branches and cleanup  |
| `/audit-plans`      | All open erk-plans | Identify stale or completed plans    |

**Characteristics:**
- Multi-phase workflow with data collection and analysis
- Presents categorized tables of results
- User selects items to act upon
- Higher context cost (reads many items)

### Single-Item Assessment Commands

Single-item assessment commands analyze one specific item in detail:

| Command             | Input           | Purpose                                      |
| ------------------- | --------------- | -------------------------------------------- |
| `/check-relevance`  | Issue number    | Assess if PR/plan work is already implemented |

**Characteristics:**
- Focused, inline during development workflow
- Evidence-based verdict with classification
- Lower context cost (single item analysis)
- Immediate actionability

## Design Decision: When to Use Each Pattern

**Use batch audit when:**
- Periodic cleanup operations
- Comprehensive repository health checks
- User needs to see "big picture" of staleness

**Use single-item assessment when:**
- User is actively working on or reviewing specific item
- Quick decision needed during development flow
- Deep analysis of one item is more valuable than broad scan

## Related Documentation

- [Command Organization](command-organization.md) - CLI command hierarchy decisions
- [Plan Lifecycle](../planning/lifecycle.md) - Plan states and transitions
```

---

#### 2. Update plan lifecycle documentation with verdict categories

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a new section after "Which Phase Am I In?" or in an appropriate location:

```markdown
## Plan Relevance Assessment

When evaluating whether a plan should be implemented or closed, use the verdict classification system from `/local:check-relevance`:

| Verdict               | Overlap | Meaning                                                     |
| --------------------- | ------- | ----------------------------------------------------------- |
| SUPERSEDED            | >80%    | Work is already implemented in master                       |
| PARTIALLY_IMPLEMENTED | 30-80%  | Some work exists, plan may need scoping adjustment          |
| DIFFERENT_APPROACH    | N/A     | Same problem solved with different implementation           |
| STILL_RELEVANT        | <30%    | Work is not yet implemented, plan remains valid             |
| NEEDS_REVIEW          | Unclear | Manual review required, evidence inconclusive               |

**Usage:** Run `/local:check-relevance <plan-issue-number>` to assess a plan's current relevance before deciding to implement or close it.
```

---

#### 3. Document cross-artifact linking capability

**Location:** `docs/learned/planning/cross-artifact-analysis.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
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
```

---

### LOW Priority

#### 1. Reference 9-phase analysis workflow (optional)

**Location:** Consider `docs/learned/architecture/agent-workflow-patterns.md` or reference in existing docs
**Action:** REFERENCE (no action needed now)
**Source:** [Impl]

**Rationale:** The 9-phase workflow structure in `/local:check-relevance` is well-documented within the command file itself. If future commands need similar multi-phase analysis patterns, they can reference this command as an example. No separate documentation needed at this time.

---

## Contradiction Resolutions

**Status: NO CONTRADICTIONS**

The analysis found no conflicts between new and existing documentation. The `/local:check-relevance` command's verdict classification system and evidence-based approach is consistent with existing staleness detection patterns in `/audit-branches.md` and `/audit-plans.md`.

---

## Prevention Insights

No errors or failed approaches were documented during this planning session. The implementation proceeded smoothly without backtracking or corrections.

---

## Tripwire Additions

Add this to the frontmatter of `docs/learned/planning/lifecycle.md`:

### For `docs/learned/planning/lifecycle.md`

```yaml
tripwires:
  - action: "implementing custom PR/plan relevance assessment logic"
    warning: "Reference `/local:check-relevance` verdict classification system first. Use SUPERSEDED (80%+ overlap), PARTIALLY_IMPLEMENTED (30-80% overlap), DIFFERENT_APPROACH, STILL_RELEVANT, NEEDS_REVIEW categories for consistency."
```