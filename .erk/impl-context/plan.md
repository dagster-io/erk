# Documentation Plan: Fix: Ensure impl-context cleanup runs for all plan-implement setup paths

## Context

PR #7747 fixed a critical workflow routing bug in the `plan-implement` command where the `.erk/impl-context/` staging directory could leak into final PRs. The root cause was subtle: three of the five setup paths in the plan-implement workflow skipped directly to Step 3, bypassing the Step 2d cleanup entirely. Only Path 1c (fresh plan save) passed through the cleanup step.

The fix introduced a **convergence point architecture** — a reusable pattern where all conditional paths must pass through a mandatory step before proceeding. In this case, all 5 setup paths now converge at Step 2d (cleanup) before reaching Step 3 (implementation). This pattern has broader applicability for any procedural documentation with multiple conditional paths.

Documentation matters here for two reasons. First, the impl-context lifecycle documentation must reflect the convergence architecture so future maintainers understand the fix. Second, the convergence point pattern itself is a valuable architectural insight that can prevent similar bugs in other workflow documentation. Agents implementing plan-implement changes need to understand that Step 2d is a mandatory convergence point, not an optional step that can be bypassed for "simpler" paths.

## Raw Materials

https://gist.github.com/schrockn/9015c8ec72cac3da46fb9dafad61cb09

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Convergence Point Pattern

**Location:** `docs/learned/documentation/convergence-points.md`
**Action:** CREATE
**Source:** [PR #7747], [Impl]

**Draft Content:**

```markdown
---
title: Convergence Points in Procedural Documentation
read_when:
  - writing procedural documentation with multiple conditional paths
  - modifying workflow routing in command documentation
  - debugging why a mandatory step was skipped
tripwires:
  - action: "modifying procedural workflow routing in command documentation"
    warning: "Verify ALL conditional paths pass through mandatory convergence points. PR #7747 fixed a bug where paths skipped directly to Step 3, bypassing cleanup. Mark convergence points explicitly with '(All Paths)' notation."
    score: 6
---

# Convergence Points in Procedural Documentation

A convergence point is a step in procedural documentation that ALL conditional paths must execute before proceeding, regardless of which path was taken.

## When to Use

Use convergence points when:

- Multiple conditional paths exist (e.g., "if X, skip to Step 3; if Y, skip to Step 4")
- A mandatory operation must run regardless of path (e.g., cleanup, validation, initialization)
- The operation has side effects that later steps depend on

## Requirements

1. **Explicit marking**: Use notation like "Step X (All Paths)" to make convergence visible
2. **Idempotent operations**: The step must work correctly regardless of preconditions from any path
3. **Routing verification**: When modifying workflow, verify all paths reach the convergence point

## Example

<!-- Source: .claude/commands/erk/plan-implement.md -->

In `plan-implement.md`, Step 2d is a convergence point. All 5 setup paths (1a without tracking, 1a with tracking, 1a-file, 1b, 1c) converge at Step 2d before reaching Step 3. The cleanup uses `git rm -rf` which succeeds even if the directory does not exist (idempotent).

## Related Documentation

- [impl-context.md](../planning/impl-context.md) — Example of convergence point in practice
```

---

#### 2. Update impl-context Cleanup Section

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [PR #7747], [Impl]

**Draft Content:**

Update the "Cleanup" section (starting at line 36) to reflect the convergence point architecture. The current text describes "Three cleanup paths exist" which is now outdated. Replace with:

```markdown
### Cleanup

The directory is cleaned up via a convergence point architecture. All 5 setup paths in plan-implement converge at Step 2d before proceeding to Step 3:

1. **`setup_impl_from_issue.py`** (Phase 1, read-only) — Reads `plan.md` and `ref.json`, copies content into `.impl/`, but deliberately does NOT delete the directory. Deletion is deferred to the git cleanup phase.
   <!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py -->

   See the comment near line 202: "Do not delete here — Step 2d in plan-implement.md handles git rm + commit + push"

2. **`plan-implement.md` Step 2d** (Phase 2, convergence point) — All 5 setup paths converge here. Performs the actual deletion with `git rm -rf .erk/impl-context/ && git commit && git push`. This deferred approach ensures removal is committed, not just deleted from the local filesystem. The `git rm -rf` command is idempotent — it succeeds even if the directory does not exist.
   <!-- Source: .claude/commands/erk/plan-implement.md, Step 2d -->

3. **`plan-implement.yml` CI workflow** — Safety net for remote execution.
```

Update the "Why It Can Leak" section to reflect that the bug was fixed:

```markdown
### Why It Can Leak

Prior to PR #7747, if a setup path skipped directly to Step 3, the convergence point (Step 2d) was bypassed and cleanup never ran. The fix ensures ALL paths pass through Step 2d. The key failure mode remains confusing "delete from disk" (shutil.rmtree) with "remove from git tracking" (git rm + commit + push).
```

---

#### 3. Tripwire: Sync Before Implementation

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add new tripwire)
**Source:** [Impl]

**Draft Content:**

Add this tripwire to the existing tripwires file:

```markdown
- action: "proceeding to implementation when .impl/ exists with has_issue_tracking: true"
  warning: "ALWAYS call setup-impl-from-issue <issue_number> before proceeding, even if impl-init returns valid. This syncs the branch with remote changes and catches parallel implementations early. Without this sync, local and remote commits may diverge with duplicate content, requiring manual rebase resolution."
  score: 6
```

Context: The session analysis revealed that local and remote agents implemented the same plan in parallel, causing branch divergence. The fix is to always sync with remote before starting implementation work, regardless of local `.impl/` validity.

---

#### 4. Tripwire: Convergence Point Verification

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE (add new tripwire)
**Source:** [PR #7747]

**Draft Content:**

Add this tripwire to the documentation tripwires file:

```markdown
- action: "modifying procedural workflow routing in command documentation"
  warning: "Verify ALL conditional paths pass through mandatory convergence points. PR #7747 fixed a bug where three setup paths skipped Step 2d (cleanup), routing directly to Step 3. Mark convergence points explicitly with '(All Paths)' notation."
  score: 6
```

Context: Workflow routing bugs can cause critical cleanup steps to be skipped. When paths say "skip to Step N", verify that no mandatory steps between the current step and N are bypassed.

---

### MEDIUM Priority

#### 5. Branch Divergence Resolution

**Location:** `docs/learned/planning/draft-pr-branch-sync.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a new section on resolving branch divergence when local and remote have identical content:

```markdown
## Divergence with Identical Content

When local and remote branches diverge but have identical content (parallel implementations of the same plan), git status shows "Your branch and 'origin/branch' have diverged" but `git diff origin/branch..HEAD` returns empty.

**Resolution**: Use `git pull --rebase`. Git automatically skips duplicate commits with the message "skipped previously applied commit". Do NOT use `git push --force` — the remote content is identical and should be preserved.

**Detection**: Check `git diff origin/branch..HEAD` before deciding on resolution strategy. If empty, the divergence is superficial (same content, different hashes).
```

---

#### 6. Tripwires as Documentation Quality Signal

**Location:** `docs/learned/ci/tripwires-quality-feedback.md`
**Action:** CREATE
**Source:** [PR #7747]

**Draft Content:**

```markdown
---
title: Tripwires as Documentation Quality Signal
read_when:
  - analyzing why a tripwire keeps firing on PRs
  - investigating root cause of repeated tripwire violations
  - improving documentation based on CI feedback
---

# Tripwires as Documentation Quality Signal

Tripwire violations can indicate unclear or incorrect documentation, not just code problems. When the same tripwire fires repeatedly, investigate whether the documentation it references is accurate.

## Feedback Loop

1. Tripwire fires on PR (e.g., "found .erk/impl-context/ in diff")
2. Investigate: Is this a code bug or a documentation bug?
3. If documentation: Fix the docs, violation disappears
4. If code: Fix the code, but also check if docs need updating

## Example

PR #7747 tripwire violation caught `.erk/impl-context/plan.md` in the PR diff. Investigation revealed the documentation incorrectly showed three paths skipping directly to Step 3, bypassing the cleanup step. The fix was to update the workflow routing in the command documentation, not to change any code.

## Related Documentation

- [impl-context.md](../planning/impl-context.md) — The doc that was fixed based on tripwire feedback
```

---

#### 7. Empty erk pr submit Output

**Location:** `docs/learned/pr-operations/erk-pr-submit.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

````markdown
---
title: erk pr submit Behavior
read_when:
  - confused by empty erk pr submit output
  - verifying PR submission status
---

# erk pr submit Behavior

## Empty Output is Normal

When `erk pr submit` returns empty output, this is expected behavior indicating the PR already exists and the branch is up-to-date with remote. No action was needed.

## Verification

Instead of retrying `erk pr submit`, verify PR state with:

```bash
# Check if PR exists
gh pr list --head <branch-name>

# Check PR validation rules
erk pr check
```
````

## Common Scenarios

| Output        | Meaning                  | Action             |
| ------------- | ------------------------ | ------------------ |
| Empty stdout  | PR exists, branch synced | No action needed   |
| PR URL        | New PR created           | Verify and monitor |
| Error message | Submission failed        | Debug and retry    |

````

---

#### 8. Idempotent Cleanup Operations

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE (expand existing content)
**Source:** [PR #7747]

**Draft Content:**

Add a subsection to the Cleanup section explaining idempotency:

```markdown
### Idempotency Requirement

Cleanup operations at convergence points must be idempotent — they must succeed regardless of which setup path was taken. Different paths leave the workspace in different states, but the cleanup step must handle all of them.

In Step 2d, `git rm -rf .erk/impl-context/` is idempotent because:
- If the directory exists and is tracked: removes it from git
- If the directory does not exist: exits successfully (no error)
- If the directory exists but is untracked: exits successfully (does not fail)

This is why the cleanup uses `git rm -rf` instead of checking existence first. An existence check would introduce path-specific logic that could be wrong for some paths.
````

---

#### 9. Plan-Implement Workflow Routing

**Location:** `docs/learned/cli/plan-implement.md`
**Action:** UPDATE (verify accuracy)
**Source:** [PR #7747]

**Draft Content:**

Verify this doc reflects the convergence point architecture. If it describes setup paths, ensure all paths show convergence at Step 2d:

- Path 1a (no tracking) -> Step 2d -> Step 3
- Path 1a (with tracking) -> setup-impl-from-issue -> Step 2d -> Step 3
- Path 1a-file -> Step 2d -> Step 3
- Path 1b -> Step 2d -> Step 3
- Path 1c -> Step 2 -> 2b -> 2c -> Step 2d -> Step 3

Add cross-reference to `docs/learned/documentation/convergence-points.md` if workflow path routing is described.

---

#### 10. Update Existing Cleanup Tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (refine existing tripwire)
**Source:** [PR #7747]

**Draft Content:**

The existing tripwire about "removing git-tracked temporary directories in setup scripts" should reference the convergence pattern. Update the warning to:

```markdown
- action: "removing git-tracked temporary directories in setup scripts"
  warning: "Defer deletion to the convergence point (git rm + commit + push), not shutil.rmtree(). The setup script reads files but does NOT delete — deletion happens at the convergence point where ALL paths converge. See impl-context.md for the pattern."
  score: 8
```

---

## Contradiction Resolutions

No contradictions found. All existing documentation is consistent. The ExistingDocsChecker verified all file path references in relevant docs:

- `docs/learned/planning/impl-context.md`: All 4 file references verified
- `docs/learned/cli/plan-implement.md`: All 2 file references verified
- `docs/learned/planning/worktree-cleanup.md`: All 3 file references verified
- `docs/learned/planning/reliability-patterns.md`: All 2 file references verified

---

## Stale Documentation Cleanup

No stale documentation found. All referenced files in existing documentation exist and are current.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Branch Divergence from Parallel Implementation

**What happened:** Local agent and remote agent both implemented the same plan (PR #7747), resulting in identical commits with different hashes (local: `2fabc5379`, remote: `917fae755`).

**Root cause:** The local agent did not sync with remote before starting implementation. Both agents saw `impl-init` return valid and proceeded independently.

**Prevention:** Always call `setup-impl-from-issue <number>` before implementation when `has_issue_tracking: true`, even if `.impl/` is already valid. This syncs with remote and catches parallel implementations early.

**Recommendation:** TRIPWIRE (added as item #3 above)

### 2. Empty Tool Output Confusion

**What happened:** `erk pr submit` returned empty output, and the agent retried multiple times thinking it failed.

**Root cause:** Empty output is expected behavior when PR exists and branch is synced — no action was needed.

**Prevention:** Document expected empty output for idempotent operations. Use verification commands (`gh pr list`, `git status`) to confirm state instead of relying on stdout.

**Recommendation:** ADD_TO_DOC (added as item #7 above)

### 3. Missing Cleanup Execution

**What happened:** The tripwires bot caught `.erk/impl-context/plan.md` in the PR at the end of the session, indicating the cleanup step did not run or was bypassed.

**Root cause:** The remote agent's commit (pulled via rebase) already contained the leak because the remote implementation also bypassed Step 2d — demonstrating the bug the PR was fixing.

**Prevention:** The convergence point architecture ensures all paths pass through cleanup. No additional prevention needed beyond the fix itself.

**Recommendation:** CONTEXT_ONLY (documented in impl-context.md update)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Sync Before Implementation

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When `.impl/` exists with `has_issue_tracking: true`, before proceeding to implementation
**Warning:** ALWAYS call `setup-impl-from-issue <issue_number>` before proceeding, even if impl-init returns valid. This syncs with remote and catches parallel implementations early.
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire is warranted because the failure mode is silent — both agents think they are implementing correctly, but the branch diverges. The resolution (git rebase) is non-destructive but confusing, and the duplicate commits can obscure the actual change history.

### 2. Convergence Point Verification

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When modifying procedural workflow routing in command documentation
**Warning:** Verify ALL conditional paths pass through mandatory convergence points. Mark convergence points with "(All Paths)" notation.
**Target doc:** `docs/learned/documentation/tripwires.md`

This tripwire is warranted because workflow routing bugs can cause critical operations to be skipped silently. The PR #7747 bug leaked git-tracked staging directories into production PRs — a visible but confusing problem that only surfaces after the PR is created. Agents need to verify routing completeness before shipping workflow documentation changes.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Branch Divergence with Identical Content

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific resolution pattern using `git pull --rebase` when `git diff origin/branch..HEAD` is empty. This is useful knowledge but specific to a rare scenario (parallel implementations). Better documented as a section in `draft-pr-branch-sync.md` rather than a tripwire. Would warrant promotion if parallel implementations become more common.

### 2. Empty erk pr submit Output

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Confusing but not destructive. The agent retried unnecessarily but did not cause harm. Better as documentation note explaining expected behavior than as a tripwire. Does not warrant tripwire status unless agents frequently mishandle this scenario.
