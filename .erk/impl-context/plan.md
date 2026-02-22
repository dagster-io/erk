# Documentation Plan: Enable learn prompts for remote plan branches during erk land

## Context

This PR (#7784) removes a conditional guard that was preventing learn prompts from triggering for remotely-implemented plan branches during `erk land`. The guard checked `(target.is_current_branch or target.worktree_path is not None)` before invoking learn status checks, which meant remote branches (those implemented via GitHub Actions CI without a local worktree) would never receive documentation prompts at land time.

The change is architecturally significant because it completes the learn workflow's coverage across all implementation paths. Previously, only local implementations (where the developer had a worktree checked out) would trigger the learn flow. Now, remote implementations via the plan-submit/CI workflow also benefit from automated documentation capture. The underlying infrastructure (`trigger-async-learn`) already supported remote sessions via branch-based storage, making this guard removal safe.

Future agents working on the learn subsystem would benefit from understanding: (1) why this guard originally existed (to prevent learn from firing during CI implementation before review), (2) why it was removed (learn moved to land time, making the guard obsolete), and (3) how remote sessions are discovered and processed (via plan metadata fields and branch-based storage).

## Raw Materials

PR #7784

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 5     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Update learn-plan-land-flow.md with remote branch behavior

**Location:** `docs/learned/cli/learn-plan-land-flow.md`
**Action:** UPDATE
**Source:** [PR #7784]

**Draft Content:**

```markdown
## Remote Branch Learn Status Checks

As of PR #7784, learn status is checked for ALL plan branches, including those implemented remotely without a local worktree.

Previously, the land flow only checked learn status when `is_current_branch=True` or `worktree_path is not None`. This excluded remote implementations (PRs created by GitHub Actions CI workflows).

### How Remote Sessions Are Discovered

For remote plan branches, session discovery works via plan metadata fields:
- `last_session_branch`: Points to the `session/{plan_id}` branch containing session data
- `last_session_id`: Identifies the specific session within that branch

The `trigger-async-learn` infrastructure downloads remote sessions via `git show origin/{session_branch}:.erk/session/{session_id}.jsonl`.

See `src/erk/cli/commands/land_cmd.py` for the guard removal and `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` for remote session handling.
```

---

#### 2. Update learn-workflow.md with remote branch capability

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE
**Source:** [PR #7784]

**Draft Content:**

```markdown
## Remote Implementation Support

The learn workflow now triggers for all plan branches regardless of implementation location.

### Local vs Remote Implementations

- **Local implementations**: Developer has a worktree checked out; session logs stored locally
- **Remote implementations**: CI workflow creates PR; session logs stored in `session/{plan_id}` branches

Both paths now receive learn prompts at land time. The `_check_learn_status_and_prompt()` function handles both scenarios transparently.

### Non-Interactive Behavior

In non-interactive mode (common for CI/automation), the learn prompt auto-selects "trigger async learn" without user intervention. This ensures remote implementations don't block on user input.

See `src/erk/cli/commands/land_cmd.py` for the implementation.
```

---

#### 3. Add tripwire for learn status guard patterns

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7784]

**Draft Content:**

```markdown
## Learn Status Check Guards

**Trigger:** Adding conditional guards to learn status checks in land pipeline

**Warning:** Learn status checks run for ALL plan branches (local and remote). The `is_current_branch`/`worktree_path` guard was removed in PR #7784 to enable learn prompts for remote implementations. Only gate on `plan_id` existence and config settings. Remote sessions are discovered via plan metadata fields and handled by `trigger-async-learn` infrastructure.

**Trigger:** Determining whether to check learn status for a branch

**Warning:** Check learn status for ALL plan branches, not just those with local worktrees. The worktree guard was removed to support remote implementations. The `_check_learn_status_and_prompt()` function has its own safety checks (respects config, handles zero sessions, auto-selects in non-interactive mode).

**Historical context:** The guard originally prevented learn from firing during CI implementation (before review). When learn moved to land time, the guard became obsolete but remained, blocking remote branches.

**Grep pattern:** `is_current_branch or worktree_path`
```

---

### MEDIUM Priority

#### 4. Create remote-branch-learn-prompts.md

**Location:** `docs/learned/planning/remote-branch-learn-prompts.md`
**Action:** CREATE
**Source:** [PR #7784]

**Draft Content:**

```markdown
---
read-when:
  - working on learn workflow for remote implementations
  - debugging why learn prompts don't trigger for CI-created PRs
  - modifying land pipeline learn status checks
---

# Remote Branch Learn Prompts

Learn prompts now trigger for all plan branches at land time, including those implemented remotely without a local worktree.

## Historical Context

The learn workflow originally fired during CI implementation (before PR review). A guard was added to prevent this premature triggering by checking `is_current_branch or worktree_path is not None`.

When learn was moved to land time (after PR review and approval), the guard became obsolete. However, it remained and blocked remote branches because they have no local worktree.

PR #7784 removed this guard, completing learn coverage for all implementation paths.

## How Remote Sessions Work

Remote implementations store session data in `session/{plan_id}` branches rather than local worktree paths. The discovery mechanism uses plan metadata fields:

- `last_session_branch`: Branch containing session data
- `last_session_id`: Specific session identifier

The `trigger-async-learn` exec script handles remote sessions by downloading via git:
`git show origin/{session_branch}:.erk/session/{session_id}.jsonl`

## Safety Guarantees

The guard removal is safe because:

1. `trigger-async-learn` infrastructure already handles remote sessions
2. `_check_learn_status_and_prompt()` respects config overrides
3. Zero sessions are handled gracefully (no error, just skips)
4. Non-interactive mode auto-selects "trigger async learn"

## Related Files

- `src/erk/cli/commands/land_cmd.py` - Guard removal in `_validate_pr_for_landing()`
- `src/erk/cli/commands/land_pipeline.py` - Guard removal in `check_learn_status()`
- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` - Remote session handling
```

---

#### 5. Update plan-implement-workflow.md with upstream handling pattern

**Location:** `docs/learned/planning/plan-implement-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Handling Upstream Implementation Conflicts

In multi-workflow scenarios, target changes may already be applied upstream before the local agent starts work. This occurs when:

1. Remote CI workflow applies changes to the draft PR branch
2. Local agent syncs with remote via `setup-impl-from-issue`
3. Target changes are already present in the synced code

### Detection Pattern

Verify changes are already applied using git diff:

```bash
git diff master...HEAD
```

If the expected changes appear in the diff, mark tasks as complete without editing. This prevents:
- Redundant file edits
- "File modified since read" errors
- Duplicate code changes

### Recovery from Git Divergence

When `.erk/impl-context/` cleanup encounters a diverged remote:

1. Use `git pull --rebase` to sync
2. Rebase drops commits that are "already upstream"
3. This confirms cleanup was already done by upstream workflow

The cleanup is idempotent - if upstream already performed it, the local commit simply disappears during rebase.

See session c79db366 for an example of this pattern in practice.
```

---

## Contradiction Resolutions

No contradictions found between existing documentation and the new implementation.

The existing-docs-checker correctly identified this as a **design change** from documented behavior rather than a documentation contradiction. The worktree guard was intentional, and this PR removes it to enable a new capability.

## Stale Documentation Cleanup

No stale documentation detected. The existing-docs-checker verified all references point to existing files with no phantom references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Git Push Rejected After Cleanup Commit

**What happened:** Attempted to push `.erk/impl-context/` cleanup commit but remote had diverged.

**Root cause:** Remote workflow had already performed the cleanup in a parallel execution path. The local branch was behind the remote.

**Prevention:** Always use `git pull --rebase` before pushing cleanup commits. If the commit is "already upstream", rebase will drop it harmlessly.

**Recommendation:** ADD_TO_DOC (added to plan-implement-workflow.md update above)

### 2. File Modified Since Read Error

**What happened:** Agent read `land_cmd.py`, then `git pull --rebase` brought upstream changes, then agent tried to edit based on stale content.

**Root cause:** Rebase changed file contents between read and edit operations.

**Prevention:** After any git pull/rebase operation, re-read files before editing. Alternatively, check `git diff` to verify if changes are already applied.

**Recommendation:** CONTEXT_ONLY (standard git workflow awareness, MEDIUM severity but LOW frequency)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Remote branch learn status guard removal

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1, Repeated pattern +1)

**Trigger:** Before adding conditional guards to learn status checks in land pipeline

**Warning:** Learn status checks now run for ALL plan branches (local and remote). The is_current_branch/worktree_path guard was removed in PR #7784 to enable learn prompts for remote implementations. Only gate on plan_id existence and config settings.

**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire is warranted because the guard pattern was not self-documenting. The condition `(target.is_current_branch or target.worktree_path is not None)` requires context to understand why it existed and why removal is safe. Without this tripwire, a future agent might re-introduce a similar guard thinking it protects against some edge case.

The pattern appeared in two locations (`land_cmd.py` and `land_pipeline.py`), indicating it was a deliberate architectural decision that is now superseded.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Upstream implementation handling

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)

**Notes:** This pattern only occurs in specific CI scenarios where multiple workflows operate on the same draft PR branch. The session demonstrated robust handling via git diff verification, but the low frequency (only in remote implementation + local agent overlap scenarios) keeps it below the cross-cutting threshold. If this pattern recurs in future sessions, consider promoting to a full tripwire.
