# Consolidated Documentation Plan

> **Consolidates:** #6051, #6049, #6047, #6046, #6038, #6033, #6032, #6026

## Source Plans

| #     | Title                                                                 | Items Merged |
| ----- | --------------------------------------------------------------------- | ------------ |
| 6051  | Fix detached HEAD state after landing PR from root worktree           | 4 items      |
| 6049  | Auto-fix Graphite Tracking Divergence                                 | 11 items     |
| 6047  | Analysis: PR #6023 .worker-impl/ Not Cleaned Up                       | 10 items     |
| 6046  | Unify Local/Remote Command Pattern                                    | 9 items      |
| 6038  | Fix Plan Save Workflow Bugs                                           | 8 items      |
| 6033  | Phase 5 - GitHub Actions Workflow for Objective Reconciler            | 8 items      |
| 6032  | Add Longer Timeout Guidance for Background Agents                     | 4 items      |
| 6026  | Complete howto/pr-checkout-sync.md Documentation                      | 6 items      |

## Investigation Findings

### What Already Exists (IMPLEMENTED - Skip These)

Based on deep codebase investigation, the following documentation items from the source plans **already exist** and should be skipped:

1. **#6047 - .worker-impl/ cleanup patterns** - EXISTS at `docs/learned/ci/erk-impl-workflow-patterns.md` (comprehensive, 125 lines)
2. **#6047 - Cleanup tripwire** - EXISTS in `docs/learned/tripwires.md` (line 170)
3. **#6049 - Graphite cache invalidation** - EXISTS at `docs/learned/architecture/graphite-cache-invalidation.md`
4. **#6049 - Parent branch divergence detection** - EXISTS at `docs/learned/architecture/git-graphite-quirks.md` (lines 225-258)
5. **#6032 - Timeout guidance in replan commands** - EXISTS in `.claude/commands/erk/replan.md` and `local/replan-learn-plans.md`
6. **#6026 - pr-sync-divergence** - EXISTS at `docs/learned/cli/commands/pr-sync-divergence.md` (comprehensive, 86 lines)

### Overlap Analysis

Multiple plans touch the same areas:
- **Git/Graphite divergence**: #6049, #6051, #6026 all touch divergence concepts
- **Workflow patterns**: #6047, #6033, #6038 all touch CI/workflow automation
- **Session management**: #6038, #6032 both touch session-related patterns

## Remaining Gaps (Consolidated Implementation Plan)

### HIGH Priority - Tripwires

These are critical "before you do X" warnings that prevent common bugs:

#### 1. Multi-Worktree Checkout Conflict Tripwire (from #6051)

**File:** `docs/learned/tripwires.md`
**Action:** ADD entry

```markdown
**CRITICAL: Before calling checkout_branch() in a multi-worktree repository** → Read [Multi-Worktree State Handling](architecture/multi-worktree-state.md) first. Verify the target branch is not already checked out in another worktree using `git.worktree.find_worktree_for_branch()`. Git enforces a single-checkout constraint - attempting to checkout a branch held elsewhere causes silent state corruption or unexpected failures.
```

#### 2. Session Marker Write Timing Tripwire (from #6038)

**File:** `docs/learned/tripwires.md`
**Action:** ADD entry

```markdown
**CRITICAL: Before using session-scoped markers in exec scripts** → Read [Session-Based Plan Deduplication](planning/session-deduplication.md) first. Session markers enable idempotency in command retries. Always write markers AFTER successful operation completion, never before. Use triple-check guard on marker read: file exists AND content is valid AND expected type (numeric for issue numbers).
```

#### 3. Graphite SHA Tracking Divergence Tripwire (from #6049)

**File:** `docs/learned/tripwires.md`
**Action:** ADD entry

```markdown
**CRITICAL: Before comparing git SHA to Graphite's tracked SHA for divergence detection** → Read [Git and Graphite Edge Cases](architecture/git-graphite-quirks.md) first. Ensure both `commit_sha` and `graphite_tracked_sha` are non-None before comparison. Returning False when either is None avoids false negatives on new branches.
```

---

### HIGH Priority - New Documentation Files

#### 4. Multi-Worktree State Handling (from #6051)

**File:** `docs/learned/architecture/multi-worktree-state.md`
**Action:** CREATE

**Content outline:**
- The Single-Checkout Constraint (git enforces branch only in one worktree)
- Query Before Action Pattern using `find_worktree_for_branch()`
- Conditional execution based on query result
- Example: Land command cleanup with trunk checkout
- Anti-patterns to avoid

#### 5. Local/Remote Command Group Pattern (from #6046)

**File:** `docs/learned/cli/local-remote-command-groups.md`
**Action:** CREATE

**Content outline:**
- The `@click.group(invoke_without_command=True)` pattern
- `ErkCommandGroup` helper class usage
- Context check pattern for default behavior
- Migration checklist from separate commands
- Reference implementations in codebase

---

### MEDIUM Priority - Documentation Updates

#### 6. Branch Cleanup Update - Detached HEAD Recovery (from #6051)

**File:** `docs/learned/erk/branch-cleanup.md`
**Action:** UPDATE (add section)

Add section documenting:
- Worktree state after landing PRs
- Why checkout may fail (trunk held elsewhere)
- Expected behavior table
- Recovering from detached HEAD

#### 7. Git-Graphite Quirks Update - SHA Tracking Divergence (from #6049)

**File:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE (add section)

Add section on Graphite SHA Tracking Divergence:
- Problem: `.graphite_cache_persist` branchRevision becomes stale after rebase/restack
- Detection: comparing `commit_sha` vs `graphite_tracked_sha`
- Auto-Fix: `retrack_branch()` method pattern
- When divergence occurs

#### 8. Objective Commands Update - Session Idempotency (from #6038)

**File:** `docs/learned/cli/objective-commands.md`
**Action:** UPDATE (add section)

Add section on Session-Based Idempotency:
- Behavior when `--session-id` is provided
- JSON response with `skipped_duplicate` field
- Scope (within session vs cross-session)

#### 9. Exec Script Testing Update - Idempotent Commands (from #6038)

**File:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE (add section)

Add section on Testing Idempotent Commands:
- Pattern: Two sequential invocations
- Assertions to verify
- Format-specific testing

---

### LOW Priority - New Documentation Files

#### 10. PR Checkout Sync Howto Completion (from #6026)

**File:** `docs/howto/pr-checkout-sync.md`
**Action:** REPLACE skeleton with full content

Replace TODO sections with actual documentation:
- Overview (4 use cases)
- Checking Out a PR (`erk pr co` with flags)
- Syncing with Remote (Git-only and Graphite modes)
- Making Changes (edit → Claude Code → /erk:pr-address flow)
- Submitting Updates (`erk pr submit`)
- Landing (`erk land` with flags)
- Common Scenarios table
- See Also with cross-references

#### 11. Objective Reconciler Workflow (from #6033)

**File:** `docs/learned/ci/objective-reconciler-workflow.md`
**Action:** CREATE

**Content outline:**
- Workflow overview (manual dispatch only initially)
- Input parameters (dry_run, objective number)
- Secret requirements (ERK_QUEUE_GH_PAT + ANTHROPIC_API_KEY)
- Concurrency control
- Cost model (~$0.003/objective)

#### 12. Command Group Testing (from #6046)

**File:** `docs/learned/testing/command-group-testing.md`
**Action:** CREATE

**Content outline:**
- Test invocation format changes
- Bulk migration with sed
- Testing both variants pattern

---

### SKIP - Already Implemented or Low Value

The following items from source plans are either already implemented or provide low value:

- #6047: All items (workflow patterns comprehensively documented)
- #6032: Timeout guidance (already in command files)
- Items marked as "CONTEXT_ONLY" in source plans

---

## Implementation Steps

### Step 1: Add Tripwires (3 entries)
1. Edit `docs/learned/tripwires.md`
2. Add multi-worktree checkout conflict tripwire
3. Add session marker write timing tripwire
4. Add Graphite SHA tracking divergence tripwire

### Step 2: Create New HIGH Priority Docs (2 files)
1. Create `docs/learned/architecture/multi-worktree-state.md`
2. Create `docs/learned/cli/local-remote-command-groups.md`

### Step 3: Update Existing Docs (4 files)
1. Update `docs/learned/erk/branch-cleanup.md` with detached HEAD section
2. Update `docs/learned/architecture/git-graphite-quirks.md` with SHA tracking section
3. Update `docs/learned/cli/objective-commands.md` with session idempotency
4. Update `docs/learned/testing/exec-script-testing.md` with idempotent command testing

### Step 4: Create/Complete LOW Priority Docs (3 files)
1. Complete `docs/howto/pr-checkout-sync.md` (replace skeleton)
2. Create `docs/learned/ci/objective-reconciler-workflow.md`
3. Create `docs/learned/testing/command-group-testing.md`

---

## Verification

1. Run `erk docs sync` to regenerate tripwires.md index
2. Run `make format` to ensure markdown formatting
3. Verify all new docs have proper frontmatter with `title` and `read_when` fields
4. Verify tripwires.md entries link to their target documents
5. Check cross-references between related documents

---

## Attribution

| Category | Source Issues |
| -------- | ------------- |
| Tripwires | #6051, #6038, #6049 |
| Architecture docs | #6051, #6049 |
| CLI docs | #6046, #6038 |
| Testing docs | #6046, #6038 |
| Howto docs | #6026 |
| CI docs | #6033 |

---

## Related Documentation

Skills to load during implementation:
- `learned-docs` - For writing/modifying docs in docs/learned/
- `dignified-python` - If any Python examples needed