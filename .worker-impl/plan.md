# Plan: Consolidated erk-learn Documentation Plan

> **Consolidates:** #6001, #5998, #5996, #5995, #5992, #5985

## Source Plans

| #    | Title                                                           | Status             |
| ---- | --------------------------------------------------------------- | ------------------ |
| 6001 | Add --objective option to erk objective reconcile command       | Docs needed        |
| 5998 | Consolidated erk-learn Documentation Plan                       | FULLY_IMPLEMENTED  |
| 5996 | Add Background Agent Completion Requirement to Replan Commands  | Docs needed        |
| 5995 | Fix Keyword-Only Parameter False Positives in Code Review       | Docs needed        |
| 5992 | Clarify land.sh deferred cleanup in confirmation messages       | FULLY_IMPLEMENTED  |
| 5985 | Phase 3: CLI Command with Dry-Run                               | Docs needed        |

## What Changed Since Original Plans

- **#5998 fully implemented**: Commit 5983a95b merged consolidated learn documentation including `docs/learned/planning/learn-workflow.md` agent tier architecture
- **#5992 fully implemented**: Commit a68989e clarified land.sh messages with "After landing," prefix pattern
- **Step 4e CRITICAL section added**: `/erk:replan` workflow now includes mandatory background agent completion gate
- **Keyword-only filtering implemented**: Code review now filters ABC/Protocol methods correctly
- **Reconcile command implemented**: `--objective` and `--dry-run` flags fully functional

## Investigation Findings

### Plans That Are FULLY_IMPLEMENTED (No Action Needed)

**#5998** - All items merged in commit 5983a95b:
- Agent tier architecture documented in learn-workflow.md
- Stateless file-based composition documented
- Model selection rationale documented

**#5992** - All items merged:
- "After landing," prefix pattern implemented in land_cmd.py
- Confirmation messages clarified for deferred cleanup

### Corrections to Original Plans

**#6001**:
- Bug found: `reconcile_cmd.py:86` uses `user_output(f"[{plan_status}]")` without Rich markup escaping
- Tripwire for Rich escaping already exists in tripwires.md

**#5996**:
- Step 4e section already exists in `/erk:replan` at lines 186-206
- Documentation still needed to explain rationale

**#5995**:
- Filtering implemented in `code_review.py:61-67`
- Missing: Docstring convention for exception patterns

**#5985**:
- All code implemented (issue_exists, dry-run, objective reconcile)
- All 7 documentation items still NOT_IMPLEMENTED

### Overlap Analysis

- **#6001 and #5985** both propose `docs/learned/cli/objective-commands.md` - MERGED into single item
- **#5995 and #5985** both reference code review patterns - DEDUPLICATED

## Remaining Documentation Gaps

### HIGH Priority

1. **`docs/learned/cli/objective-commands.md`** _(from #6001, #5985)_
   - Document `erk objective reconcile` command with `--objective` and `--dry-run` flags
   - Include tripwire for Rich markup escaping in status output

2. **`docs/learned/architecture/gateway-abc-implementation.md` UPDATE** _(from #5985)_
   - Add `issue_exists()` LBYL pattern documentation
   - Document when to use 4-file vs 5-file gateway patterns

3. **`docs/learned/planning/agent-delegation.md` UPDATE** _(from #5996)_
   - Add "Background Agent Synchronization" section
   - Document Step 4e rationale and TaskOutput usage pattern

### MEDIUM Priority

4. **`docs/learned/cli/code-review-filtering.md`** _(from #5995)_
   - Document ABC/Protocol exception filtering for keyword-only parameters
   - Include docstring convention for edge case patterns

5. **`docs/learned/architecture/lbyl-gateway-pattern.md`** _(from #5985)_
   - Document "Look Before You Leap" pattern for gateway operations
   - Example: `issue_exists()` before `get_issue()`

### LOW Priority (Tripwire-only)

6. **Tripwire addition** _(from #5996)_
   - Before modifying parallel agent spawning in consolidation workflows
   - Warning about Step 4e synchronization requirement

## Implementation Steps

1. **Create `docs/learned/cli/objective-commands.md`** _(from #6001, #5985)_
   - Document reconcile command usage
   - Add Rich escaping tripwire
   - Include dry-run flag pattern

2. **Update `docs/learned/architecture/gateway-abc-implementation.md`** _(from #5985)_
   - Add issue_exists() LBYL section after "Read-Only vs Mutation Methods"
   - Document 4-file simplified pattern rationale

3. **Update `docs/learned/planning/agent-delegation.md`** _(from #5996)_
   - Add "Background Agent Synchronization" section
   - Include TaskOutput block:true pattern

4. **Create `docs/learned/cli/code-review-filtering.md`** _(from #5995)_
   - Document filtering logic for false positives
   - Include docstring convention example

5. **Create `docs/learned/architecture/lbyl-gateway-pattern.md`** _(from #5985)_
   - Document existence-check-first pattern
   - Cross-reference gateway ABC doc

6. **Update `docs/learned/tripwires.md`** _(from #5996)_
   - Add parallel agent synchronization tripwire

## Attribution

Items by source plan:
- **#6001**: Step 1 (objective-commands.md)
- **#5998**: No items (fully implemented)
- **#5996**: Steps 3, 6 (agent-delegation.md, tripwire)
- **#5995**: Step 4 (code-review-filtering.md)
- **#5992**: No items (fully implemented)
- **#5985**: Steps 1, 2, 5 (objective-commands.md, gateway-abc.md, lbyl-pattern.md)

## Related Documentation

- `dignified-python` skill (for doc formatting standards)
- `learned-docs` skill (for frontmatter and routing)
- `docs/learned/index.md` (to update with new docs)

## Verification

After implementation:
1. Run `make format` to ensure consistent formatting
2. Run `erk docs validate` to check frontmatter
3. Verify `docs/learned/index.md` includes all new docs
4. Check tripwires.md regenerates correctly with `erk docs sync`