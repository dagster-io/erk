---
title: Roadmap Mutation Patterns
read_when:
  - "deciding between surgical vs full-body roadmap updates"
  - "implementing roadmap mutation logic"
  - "understanding when to use update-roadmap-step vs objective-update-with-landed-pr"
tripwires:
  - action: "using full-body update for single-cell changes"
    warning: "Full-body updates replace the entire table. For single-cell PR updates, use surgical update (update-roadmap-step) to preserve other cells and avoid race conditions."
  - action: "using surgical update for complete table rewrites"
    warning: "Surgical updates only change one cell. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr)."
last_audited: "2026-02-05 12:25 PT"
audit_result: edited
---

# Roadmap Mutation Patterns

Erk provides two patterns for mutating objective roadmap tables: **surgical updates** (single-cell changes) and **full-body updates** (complete table rewrites). Choosing the right pattern prevents race conditions and preserves data integrity.

## Pattern Comparison

| Pattern   | Command                           | Scope          | Use Case                         |
| --------- | --------------------------------- | -------------- | -------------------------------- |
| Surgical  | `update-roadmap-step`             | Single PR cell | Linking plan to step after save  |
| Full-body | `objective-update-with-landed-pr` | Entire table   | Rewriting roadmap after PR lands |

## Surgical Update Pattern

**Command**: `erk exec update-roadmap-step <issue-number> --step <step-id> --pr <pr-ref>`

**What it does**:

- Finds the step row by step ID (e.g., `1.3`, `2.1`)
- Replaces the PR cell (4th column) with the new value
- Computes display status from PR value (done/in-progress/pending) and sets the status cell
- Preserves all other cells (description, other steps)

**Example**:

```bash
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"
```

**Result** (before → after):

```diff
| Step | Description | Status | PR |
- | 1.3 | Add feature | pending | - |
+ | 1.3 | Add feature | in-progress | plan #6464 |
```

The status is computed from the PR value: `#NNN` → done, `plan #NNN` → in-progress, empty → pending.

### When to Use Surgical Updates

1. **Plan-save workflow**: After `erk plan save`, link the saved plan to its roadmap step
2. **PR creation workflow**: After `erk pr submit`, link the created PR to its step
3. **Single step updates**: Any scenario where only one step's PR reference changes

**Advantages**:

- Atomic operation (no race conditions)
- Preserves manual edits to other cells
- Simple mental model: "set step X's PR to Y"

### Implementation (update_roadmap_step.py)

> **Source**: See [`update_roadmap_step.py`](../../../src/erk/cli/commands/exec/scripts/update_roadmap_step.py)

The surgical update uses regex to find the step row by ID, then replaces both the status cell (3rd column, computed from PR value) and the PR cell (4th column).

**LBYL pattern**: Check if step exists before attempting replacement:

```python
if not match:
    return StepNotFound(step_id=step_id)
```

## Full-Body Update Pattern

**Command**: `erk exec objective-update-with-landed-pr <issue-number> --landed-pr <pr-number>`

**What it does**:

- Fetches current roadmap
- Finds the step linked to the landed PR
- Marks that step as `done` with PR reference
- Rewrites the **entire roadmap table** with new markdown
- May reorder, add, or remove steps (full control)

**Example**:

```bash
erk exec objective-update-with-landed-pr 6423 --landed-pr 6500
```

**Result**: Complete table rewrite, not just one cell. The landed PR's step is marked done, layout may change (e.g., collapsing completed phases).

### When to Use Full-Body Updates

1. **PR landing workflow**: After `erk land`, update roadmap to reflect landed work
2. **Roadmap restructuring**: When reordering phases or adding/removing steps
3. **Status audits**: When reviewing and batch-updating multiple step statuses
4. **Layout changes**: When collapsing completed sections or adding new phases

**Advantages**:

- Full control over table layout
- Can make multiple changes atomically
- Can add narrative sections between phases

**Disadvantages**:

- Higher risk of race conditions (entire table is rewritten)
- Overwrites any manual edits made since last fetch
- Requires parsing and regenerating full markdown

### Implementation

The full-body update is a Claude command (`/erk:objective-update-with-landed-pr`), not a standalone Python script. It uses `erk exec objective-update-context` to fetch all context (objective, plan, PR) in a single call, then the LLM rewrites the roadmap table with full control over layout changes.

**LBYL pattern**: Validate before mutation:

```python
# Check issue exists
if isinstance(issue, IssueNotFound):
    click.echo(f"Issue #{issue_number} not found")
    sys.exit(1)

# Check roadmap parsed successfully
phases, errors = parse_roadmap(issue.body)
if not phases:
    click.echo("No roadmap found")
    sys.exit(1)

# Check step with landed PR exists
step = _find_step_by_pr(phases, landed_pr_number)
if not step:
    click.echo(f"No step found with PR #{landed_pr_number}")
    sys.exit(1)
```

## When to Choose

| Scenario                        | Pattern   | Why                                         |
| ------------------------------- | --------- | ------------------------------------------- |
| Linking plan after save         | Surgical  | Only PR cell changes, rest is unchanged     |
| Linking PR after creation       | Surgical  | Only PR cell changes, rest is unchanged     |
| Marking step done after landing | Full-body | May want to reorder, collapse, or add steps |
| Fixing stale status values      | Surgical  | Quick fix, don't want to rewrite everything |
| Restructuring roadmap           | Full-body | Need full control over layout               |
| Batch status updates            | Full-body | Multiple steps changing at once             |

## LBYL Defensive Coding Examples

Both patterns follow erk's LBYL (Look Before You Leap) principle:

### Check Before Parsing

```python
# Don't assume issue exists
issue_result = github.get_issue(issue_number)
if isinstance(issue_result, IssueNotFound):
    return IssueNotFound(issue_number=issue_number)

# Don't assume roadmap parses successfully
phases, errors = parse_roadmap(issue_result.body)
if not phases:
    return RoadmapNotFound()
```

### Check Before Accessing Fields

```python
# Don't assume step exists in phases
step = None
for phase in phases:
    for s in phase.steps:
        if s.id == step_id:
            step = s
            break

if step is None:
    return StepNotFound(step_id=step_id)
```

### Check Status Before Inference

```python
# Two-tier status resolution (explicit beats inference)
if status_col in ("done", "blocked", "skipped"):
    status = status_col  # Explicit value
elif status_col in ("in-progress", "in_progress"):
    status = "in_progress"
elif status_col == "pending":
    status = "pending"
# Only infer if status is "-" or empty
elif pr_col and pr_col.startswith("#"):
    status = "done"
else:
    status = "pending"
```

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — How status inference interacts with mutations
- [Roadmap Status System](roadmap-status-system.md) — Two-tier status resolution
- [Update Roadmap Step Command](../cli/commands/update-roadmap-step.md) — Surgical update details
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — LBYL error patterns
