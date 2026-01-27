---
title: Learn Plans vs. Implementation Plans
read_when:
  - "choosing between plan types"
  - "creating erk-learn plans"
  - "understanding plan workflows"
---

# Learn Plans vs. Implementation Plans

Reference guide for understanding and selecting between learn and implementation plan types.

## Table of Contents

- [Quick Comparison](#quick-comparison)
- [Implementation Plans](#implementation-plans)
- [Learn Plans](#learn-plans)
- [When to Use Each Type](#when-to-use-each-type)

---

## Quick Comparison

| Aspect            | Implementation Plan               | Learn Plan                                |
| ----------------- | --------------------------------- | ----------------------------------------- |
| **Label**         | `erk-plan`                        | `erk-plan` + `erk-learn`                  |
| **Purpose**       | Implement code changes            | Extract learnings and write docs          |
| **Base Branch**   | Trunk (main/master)               | Parent implementation PR branch           |
| **Output**        | Code, tests, implementation       | Documentation in `docs/learned/`          |
| **Context**       | Feature requirements, codebase    | Session logs from planning/implementation |
| **Trigger**       | User request, objective planning  | After PR lands, async or manual           |
| **Workflow**      | `erk plan submit`, GitHub Actions | `/erk:learn`, async learn workflow        |
| **Branch Naming** | `P{issue}-{title}-{timestamp}`    | Same pattern (stacked on parent)          |
| **PR Type**       | Feature PR                        | Documentation PR                          |

---

## Implementation Plans

### Purpose

Implement code changes to add features, fix bugs, or refactor:

- Write source code
- Write tests
- Update configuration
- Integrate with existing systems

### Labels

**Required:** `erk-plan`

### Base Branch

**Trunk:** Implementation PRs branch off main/master (or current branch for stacking)

### Typical Output

- **Source code:** `src/erk/**/*.py`
- **Tests:** `tests/**/*.py`
- **Config:** `.erk/`, `pyproject.toml`
- **CLI commands:** `.claude/commands/**/*.md` (if adding commands)

### Creation

1. **User request:** "Implement feature X"
2. **Plan mode:** Agent enters plan mode, creates plan
3. **Save:** `/erk:plan-save` creates GitHub issue with `erk-plan` label
4. **Submit:** `erk plan submit <issue>` creates branch, PR, and dispatches workflow

### Example

**Issue #6167:** Add Context Preservation to Replan Workflow

**Changes:**

- `.claude/commands/erk/replan.md` (add Steps 6a-6b)
- `.claude/commands/local/replan-learn-plans.md` (reinforce pattern)

**Branch:** `P6167-add-context-pre-01-20-1430`

**PR:** Merges to `main`

---

## Learn Plans

### Purpose

Extract learnings from implementation and document for future agents:

- Analyze session logs (planning + implementation)
- Identify patterns, anti-patterns, tripwires
- Create/update documentation in `docs/learned/`
- Synthesize insights from multiple PRs

### Labels

**Required:** `erk-plan` + `erk-learn`

### Base Branch

**Parent implementation branch:** Learn plan stacks on the implementation PR branch

**Why:** Documentation should be created alongside the code it documents

### Typical Output

- **Documentation:** `docs/learned/**/*.md`
- **Checklists:** `docs/learned/checklists/*.md`
- **Architecture docs:** `docs/learned/architecture/*.md`
- **Tripwires:** Updates to existing docs with new tripwires

### Creation

#### Manual (User-Initiated)

```bash
/erk:learn <issue-number-or-url>
```

**Process:**

1. Fetch plan/PR for issue
2. Analyze session logs (planning + implementation)
3. Identify documentation needs
4. Create learn plan
5. Save with `--plan-type=learn` flag

#### Async (Automated)

After PR lands:

1. GitHub Action dispatches learn workflow
2. Agent analyzes sessions
3. Creates learn plan issue (with `erk-learn` label)
4. Learn plan can be submitted for async implementation

### Example

**Issue #6172:** [erk-learn] Add Context Preservation Prompting to Replan Workflow

**Parent:** Issue #6167 (implementation of Steps 6a-6b)

**Changes:**

- `docs/learned/planning/context-preservation-in-replan.md` (new)
- `docs/learned/planning/context-preservation-patterns.md` (new)
- `docs/learned/planning/lifecycle.md` (updated)
- `docs/learned/sessions/lifecycle.md` (new)

**Branch:** `P6172-erk-learn-add-context-pre-01-27-0820` (stacked on #6167 branch)

**PR:** Merges to `main` (after parent PR merges)

---

## When to Use Each Type

### Use Implementation Plan When:

- ✅ Implementing a new feature
- ✅ Fixing a bug in source code
- ✅ Refactoring existing code
- ✅ Adding CLI commands or capabilities
- ✅ Updating tests or CI workflows
- ✅ Making configuration changes

**Command:** `/erk:plan-save` (no `--plan-type` flag)

### Use Learn Plan When:

- ✅ Documenting insights from completed work
- ✅ Extracting patterns from session logs
- ✅ Creating tripwire candidates
- ✅ Writing architecture documentation
- ✅ Consolidating learnings from multiple PRs
- ✅ Adding "how to" guides for agents

**Command:** `/erk:plan-save --plan-type=learn`

### Key Decision Factor

**Question:** "Is the primary output code or documentation?"

- **Code:** Use implementation plan
- **Documentation:** Use learn plan

---

## Workflow Integration

### Implementation → Learn Cycle

1. **Implementation plan created** (issue #100)
2. **Implementation PR lands** (PR #101)
3. **Learn workflow triggered** (automatic or manual)
4. **Learn plan created** (issue #102, labeled `erk-learn`)
5. **Learn plan links to parent** (`learned_from_issue: 100`)
6. **Learn PR branches off parent** (stacked on #101 branch)
7. **Learn PR lands** (documentation committed)

### Objective Workflow

Both plan types can be associated with objectives:

**Implementation plan:**

- Tied to objective step
- Implements feature from objective
- Link: `objective_issue` in plan-header

**Learn plan:**

- Documents work from objective-related implementation
- Inherits objective link from parent
- Link: `objective_issue` in plan-header (same as parent)

---

## Plan-Header Differences

### Implementation Plan Header

```yaml
created_at: 2025-01-20T14:30:00Z
created_by: username
branch_name: P6167-add-context-pre-01-20-1430
pr_number: 5678
objective_issue: 6100 # Optional
```

### Learn Plan Header

```yaml
created_at: 2025-01-27T08:20:00Z
created_by: username
branch_name: P6172-erk-learn-add-context-pre-01-27-0820
pr_number: 5789
objective_issue: 6100 # Inherited from parent
learned_from_issue: 6167 # Points to parent implementation
```

**Key difference:** `learned_from_issue` field links learn plan to parent.

---

## Base Branch Selection

### Implementation Plans

**Default:** Trunk (main or master)

```bash
erk plan submit 6167
# Creates branch from main
```

### Learn Plans

**Default:** Parent implementation branch

```bash
erk plan submit 6172
# Reads learned_from_issue: 6167
# Gets branch_name from issue #6167
# Creates branch from P6167-add-context-pre-01-20-1430
```

**Fallback:** If parent lookup fails, falls back to trunk.

**Implementation:** See `get_learn_plan_parent_branch()` in `src/erk/cli/commands/submit.py`

---

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full plan workflow from creation to merge
- [Learn Command](../../../.claude/commands/erk/learn.md) - Learn workflow details
- [Plan Submission](../cli/pr-submission.md) - Branch creation and PR workflows
