# Plan: Multi-Plan Consolidated Replan

> Support multiple issue refs in `erk plan replan`, producing a single merged plan.

## Overview

Extend `erk plan replan` to accept multiple issue references and consolidate them into a single unified plan. Primary use case: merging related documentation plans.

**Usage:**
```bash
erk plan replan 123 456 789   # Consolidate 3 plans into 1
erk plan replan 123           # Single plan (existing behavior)
```

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/plan/replan_cmd.py` | Accept multiple issue refs |
| `.claude/commands/erk/replan.md` | Add consolidation workflow |

## Implementation

### 1. CLI Command (`replan_cmd.py`)

Change from single argument to variadic:

```python
@click.command("replan")
@click.argument("issue_refs", nargs=-1, required=True)
@click.pass_obj
def replan_plan(ctx: ErkContext, issue_refs: tuple[str, ...]) -> None:
```

Pass space-separated refs to Claude:
```python
refs_str = " ".join(issue_refs)
cmd_args = build_claude_args(config, command=f"/erk:replan {refs_str}")
```

### 2. Skill Workflow (`.claude/commands/erk/replan.md`)

**Step 1: Parse Multiple Refs**
- Split `$ARGUMENTS` on whitespace
- Extract issue numbers from each (handle URLs)
- Set `CONSOLIDATION_MODE=true` if multiple

**Step 2: Validate All Plans (Parallel)**
- Fetch each issue via `erk exec get-issue-body <number>`
- Validate all have `erk-plan` label
- Abort if any validation fails

**Step 3: Parallel Investigation**
- Launch Explore agent per plan (background)
- Investigate items, status, file mentions
- Identify overlap potential between plans

**Step 4: Consolidate Findings**
- Merge items across plans
- Deduplicate overlapping items with attribution
- Order by dependency

**Step 5: Post to Original Issues**
- Comment investigation findings on each original issue
- Note which items are being merged

**Step 6: Create Consolidated Plan**

Plan structure:
```markdown
# Plan: [Unified Title]

> **Consolidates:** #123, #456, #789

## Source Plans
| # | Title | Items Merged |
|---|-------|--------------|
| 123 | Add docs for X | 3 |
| 456 | Document Y | 2 |

## Implementation Steps
1. [Step] *(from #123)*
2. [Merged step] *(from #123, #456)*
3. [Step] *(from #456)*

## Attribution
- #123: Items 1, 2
- #456: Items 2, 3
```

**Step 7: Close All Originals**
```bash
gh issue close 123 --comment "Consolidated into #<new> with #456, #789"
gh issue close 456 --comment "Consolidated into #<new> with #123, #789"
gh issue close 789 --comment "Consolidated into #<new> with #123, #456"
```

## Backward Compatibility

Single-issue calls work exactly as before - consolidation logic only activates when multiple refs provided.

## Verification

1. Test single-plan replan still works: `erk plan replan 123`
2. Test multi-plan consolidation: `erk plan replan 123 456`
3. Verify all original issues closed with linking comments
4. Verify consolidated plan references all sources