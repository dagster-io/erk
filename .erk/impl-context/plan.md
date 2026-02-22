# Documentation Plan: Add slot options to plan-save next-steps copy and display truncated titles in TUI

## Context

This plan implements PR #7779, which enhanced the `/erk:plan-save` command with trunk-aware slot allocation guidance. The implementation demonstrates erk's characteristic pattern of behavior changes through documentation updates: no code was modified, only command documentation in `.claude/commands/erk/plan-save.md`. The command agent now detects whether the user is on trunk (main/master) or in a slot, then reorders its recommendations accordingly.

The sessions implementing this PR surfaced several valuable lessons. Most significantly, using `git merge` to sync a Graphite-tracked branch caused silent state corruption requiring manual recovery. Two separate sessions also made the same mistake with `erk exec resolve-review-threads` input format, indicating a documentation gap. The PR review comments themselves revealed a terminology standards issue, with the reviewer correcting the same phrasing problem three times.

Future agents working with Graphite workflows, PR review threads, or command output copy will benefit from this documentation. The tripwires identified here prevent state corruption and repeated trial-and-error, while the new reference docs establish standards that were previously implicit.

## Raw Materials

Materials extracted from implementation sessions and PR #7779.

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 9 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 3 |

## Documentation Items

### HIGH Priority

#### 1. Git merge breaks Graphite tracking (TRIPWIRE)

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [Impl session-92012bec]

**Draft Content:**

```markdown
## Git Sync Operations

### NEVER use `git merge` in Graphite workflows

**Trigger:** Syncing a Graphite-tracked branch with remote using git commands

**Warning:** Use `git pull --rebase` or `gt sync`, NEVER `git merge`. Merge commits break Graphite's linear history model, causing divergence warnings that block subsequent operations.

**Why this matters:** Merge commits are technically valid Git operations but incompatible with Graphite's linear history requirement. After a merge commit, `gt squash` fails with divergence errors and Graphite tracking breaks silently. Recovery requires `gt track` plus force-push, and any implementation artifacts (`.erk/impl-context/`, `.worker-impl/`) may contaminate the squashed commit.

**Correct pattern:**
- `git pull --rebase origin <branch>` for standard sync
- `gt sync` for Graphite-native sync

**Related:** See `docs/learned/planning/tripwires.md` for implementation artifact cleanup timing.
```

---

#### 2. Command output terminology standards

**Location:** `docs/learned/cli/command-output-standards.md`
**Action:** CREATE
**Source:** [PR #7779 review comments]

**Draft Content:**

```markdown
---
read-when:
  - writing user-facing command output or instructions
  - creating slash command documentation
  - editing `.claude/commands/` files
tripwires: 2
---

# Command Output Terminology Standards

Reference for writing consistent user-facing command output.

## Verb Guidelines

Use action verbs that describe the outcome, not the mechanism:

| Prefer | Avoid | Rationale |
|--------|-------|-----------|
| "Implement the plan..." | "Prepare+Implement..." | Focus on user goal, not internal steps |
| "Create a worktree..." | "Allocate a slot and create..." | User doesn't need slot internals |
| "Submit for review" | "Push and create PR" | Outcome over mechanism |

## Placeholder Formatting

Use angle brackets with descriptive names:

- `<<branch_name>>` - for values the user provides
- `<<issue_number>>` - for values from context

Do NOT use:
- Shell variables: `$branch_name`
- Curly braces: `{branch_name}`
- Generic names: `<<value>>`

## Examples

**Good output:**
```
Next steps:
1. Implement the plan in <<branch_name>> in a new worktree
2. Submit for review when ready
```

**Avoid:**
```
Next steps:
1. Prepare+Implement: source "$(erk br create --new-slot)" && erk implement --dangerous
```

## Tripwires

- **Before writing command output copy**: Check this reference for verb guidelines and placeholder format
- **When reviewer flags terminology**: Update both the specific instance AND check related commands for consistency
```

---

#### 3. resolve-review-threads JSON format

**Location:** `docs/learned/pr-operations/exec-script-reference.md`
**Action:** CREATE
**Source:** [Impl sessions 660b8210, 92012bec]

**Draft Content:**

```markdown
---
read-when:
  - using `erk exec` commands with JSON input
  - resolving PR review threads programmatically
  - encountering "is not an object" errors from exec scripts
tripwires: 1
---

# Exec Script JSON Reference

Common exec scripts that accept JSON from stdin and their expected formats.

## resolve-review-threads

Resolves PR review comment threads.

**Correct format:**
```json
[{"thread_id": "PRRT_kwDOPxC3hc5v8rc8"}, {"thread_id": "PRRT_..."}]
```

**Common mistake:**
```json
["PRRT_kwDOPxC3hc5v8rc8", "PRRT_..."]
```

This produces: `Item at index 0 is not an object`

**Pattern:** Always check `erk exec <script> -h` for exact schema before use. Help text shows the expected JSON structure.

## Tripwire

- **Before calling `erk exec` with JSON stdin**: Check `-h` output for exact schema. Many scripts require objects with named keys, not raw values.

## Related Scripts

Add additional exec script schemas here as patterns are discovered.
```

---

### MEDIUM Priority

#### 4. PR review line number divergence (TRIPWIRE)

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl session-6a355ff2]

**Draft Content:**

```markdown
## PR Review Comment Investigation

### Check for branch divergence before reading files at review line numbers

**Trigger:** Reading files at line numbers referenced in PR review comments

**Warning:** Run `git fetch && git log HEAD..origin/<branch>` to check for divergence. If remote is ahead, line numbers in review comments reference the remote version, not your local files.

**Why this matters:** PR review comments show line numbers from the GitHub PR diff view, which reflects the remote branch state at the time of review. When your local branch is behind (common when a remote agent implemented and you're reviewing), line numbers won't match your local files.

**Investigation pattern:**
1. `git fetch origin`
2. `git log HEAD..origin/<branch>` - check if remote is ahead
3. If diverged: note that line numbers reference remote version
4. Either merge/rebase first, or mentally adjust line numbers
```

---

#### 5. Trunk-aware slot allocation guidance

**Location:** `docs/learned/planning/next-steps-output.md`
**Action:** UPDATE
**Source:** [PR #7779 diff]

**Draft Content:**

```markdown
## Trunk-Aware Slot Recommendations

The `plan-save` command demonstrates a reusable UX pattern: detecting user context via git state, then reordering recommendations accordingly.

### Detection Pattern

Use `git branch --show-current` to classify location:
- **On trunk:** Result is `main`, `master`, or empty (detached HEAD)
- **In slot:** Any other branch name

### Dynamic Recommendation Ordering

Based on location, reorder slot allocation options:

| Location | First Recommendation | Second Recommendation |
|----------|---------------------|----------------------|
| On trunk | `--new-slot` (allocate new worktree) | Same-slot (stack in place) |
| In slot | Same-slot (stack in place) | `--new-slot` (allocate new worktree) |

### Why This Pattern Matters

- Users on trunk likely want to start fresh work (new slot)
- Users in a slot likely want to continue related work (same slot)
- Both options are always shown, just reordered for context

### Implementation

See `.claude/commands/erk/plan-save.md`, grep for "Trunk detection" and "Slot options block" for the implementation pattern. This approach can be reused for other context-aware command output.
```

---

#### 6. Git reflog forensics for lost commits

**Location:** `docs/learned/erk/git-recovery-patterns.md`
**Action:** CREATE
**Source:** [Impl session-aabab8a7]

**Draft Content:**

```markdown
---
read-when:
  - implementation work appears missing
  - branch seems empty but work was done
  - recovering from accidental reset or checkout
tripwires: 1
---

# Git Recovery Patterns

Systematic approaches for recovering "lost" work in worktree-based workflows.

## Reflog Forensics

When implementation work appears missing, use `git reflog` to trace what happened.

### Investigation Pattern

1. **Check reflog for recent HEAD movements:**
   ```bash
   git reflog --oneline -20
   ```
   Look for: checkout, reset, amend operations that moved HEAD

2. **Visualize branch divergence:**
   ```bash
   git log --oneline --graph --all | head -30
   ```
   Find divergent branches containing the missing work

3. **Compare with remote:**
   ```bash
   git log origin/<branch>..HEAD --oneline  # local ahead?
   git log HEAD..origin/<branch> --oneline  # remote ahead?
   ```

4. **Recovery (if work exists on remote):**
   ```bash
   git reset --hard origin/<branch>
   ```

### Empty Commit Detection

When `git show --stat` returns no files changed, the commit is empty. This typically indicates:
- Testing/checkpoint commit ("cp" message is common)
- Local experimentation that was reset

Investigate parent commits or reflog for actual work.

## Tripwire

- **When branch appears empty but work was expected**: Check `git reflog` before assuming work doesn't exist. Commits persist even after reset operations until garbage collected.
```

---

#### 7. Implementation artifact cleanup timing

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl session-92012bec]

**Draft Content:**

```markdown
## Pre-Squash Cleanup

### Clean implementation artifacts before `gt squash`

**Trigger:** Running `gt squash` after completing implementation

**Warning:** Verify `.erk/impl-context/` and `.worker-impl/` directories are removed before squashing. These directories from remote implementation branches can contaminate the squashed commit.

**Why this matters:** When a remote agent implements a plan, it may leave implementation artifacts that get pulled when you sync. If present during `gt squash`, they become part of the squashed commit, requiring a separate cleanup commit.

**Cleanup options:**
- `make clear_impl_context` - removes both directories
- Manual removal: `rm -rf .erk/impl-context/ .worker-impl/`

**Recommended workflow:**
1. Complete implementation edits
2. Run `make clear_impl_context`
3. Verify with `ls -la .erk/ | grep impl`
4. Then `gt squash`
```

---

#### 8. Slot allocation context detection

**Location:** `docs/learned/erk/slot-pool-architecture.md`
**Action:** UPDATE
**Source:** [PR #7774 implementation, gap analysis]

**Draft Content:**

```markdown
## Entry Points (Addition)

### --new-slot Flag

The `erk br create` command supports a `--new-slot` flag (added in PR #7774) to force allocation of a new worktree slot even when already in a slot.

**Default behavior:**
- On trunk (main/master): allocates new slot
- In existing slot: stacks in place (same slot)

**With --new-slot:**
- Always allocates a new slot regardless of current location

**When to use:**
- Starting unrelated work from an existing slot
- Isolating work that shouldn't stack on current branch

**User guidance:**
The `plan-save` command's next-steps output dynamically recommends `--new-slot` vs same-slot based on user location. See `docs/learned/planning/next-steps-output.md` for the context-aware recommendation pattern.
```

---

### LOW Priority

#### 9. Multi-edit verification pattern

**Location:** `docs/learned/architecture/editing-patterns.md`
**Action:** CREATE (if not exists) or UPDATE
**Source:** [Impl session-660b8210]

**Draft Content:**

```markdown
---
read-when:
  - performing bulk text replacements
  - editing multiple occurrences of similar patterns
tripwires: 1
---

# Editing Patterns

## Post-Edit Verification

After bulk Edit operations, verify completeness:

1. **Grep for remaining occurrences:**
   ```bash
   grep -r "old_pattern" path/to/files/
   ```

2. **Check no unwanted changes:**
   Review diff for unintended modifications to similar text

### Why This Matters

Bulk replacements can miss occurrences or accidentally modify similar text. A verification grep catches:
- Missed occurrences (different quoting, whitespace)
- Over-eager replacements (similar but unintended matches)

## Tripwire

- **After bulk Edit operations**: Run Grep to verify all intended changes were made and no unwanted occurrences remain.
```

---

## Stale Documentation Cleanup

**No stale documentation detected.**

All referenced code artifacts were verified to exist. Slot pool architecture docs were recently audited (2026-02-16).

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Git merge breaking Graphite tracking

**What happened:** Plan specified `git merge` to sync with remote. Merge commit created, breaking Graphite's linear history requirement. After squash, branch diverged and Graphite tracking broke.

**Root cause:** `git merge` is technically valid Git but incompatible with Graphite's linear history model. Plans authored without Graphite awareness specify merge operations that work for standard Git but fail in this context.

**Prevention:** Plans for Graphite-tracked branches must specify `git pull --rebase` or `gt sync` for syncing, never `git merge`. This should be a tripwire warning.

**Recommendation:** TRIPWIRE (score 6 - non-obvious, cross-cutting, destructive)

### 2. resolve-review-threads JSON format error

**What happened:** Two separate sessions passed `["PRRT_..."]` (string array) instead of `[{"thread_id": "PRRT_..."}]` (object array) to the exec script.

**Root cause:** Agents assumed simpler format. Help text is clear but requires proactive checking.

**Prevention:** Document the exact JSON schema in learned docs with an explicit example. Error message could be improved from "is not an object" to include expected format.

**Recommendation:** ADD_TO_DOC (exec-script-reference.md created above)

### 3. PR review line number mismatch

**What happened:** Agent read local files at line numbers from review comments, but local branch was 12 commits behind remote. Line numbers referenced remote version.

**Root cause:** PR review comments show line numbers from GitHub's diff view of the remote branch state, not local state.

**Prevention:** Before reading files at review comment line numbers, check `git log HEAD..origin/<branch>` for divergence.

**Recommendation:** TRIPWIRE (score 4 - non-obvious, repeated pattern, external tool quirk)

### 4. Implementation artifacts in squashed commit

**What happened:** `.erk/impl-context/` and `.worker-impl/` directories from remote branch contaminated the squashed commit.

**Root cause:** These directories were pulled when syncing with remote implementation branch. Squash included them.

**Prevention:** Clean implementation directories before squashing: `make clear_impl_context` or manual removal.

**Recommendation:** ADD_TO_DOC (planning/tripwires.md updated above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git merge breaks Graphite tracking

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)

**Trigger:** Before syncing a Graphite-tracked branch with remote using git commands

**Warning:** Use `git pull --rebase` or `gt sync`, NEVER `git merge`. Merge commits break Graphite's linear history model and cause silent state corruption requiring manual recovery.

**Target doc:** `docs/learned/erk/tripwires.md`

This is the highest-value tripwire from this analysis. The failure mode is silent (merge succeeds, divergence appears later), cross-cutting (affects all Graphite branches), and requires manual intervention to recover. An agent following a plan with `git merge` instructions would cause state corruption with no immediate error.

### 2. PR review line number divergence

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, External tool quirk +1)

**Trigger:** Before reading files at PR review comment line numbers

**Warning:** Run `git fetch && git log HEAD..origin/<branch>` to check for divergence. If remote is ahead, line numbers reference remote version, not local files.

**Target doc:** `docs/learned/pr-operations/tripwires.md`

This tripwire prevents confusion when reviewing remote agent work. The line number mismatch is not immediately obvious and wastes investigation time.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Empty commit detection

**Score:** 3/10 (Non-obvious +2, Silent failure +1)

**Notes:** Empty commits (no files in `--stat`) indicate checkpoint/testing. Should trigger investigation of reflog or parent commits. Not cross-cutting enough for full tripwire status. Could be promoted if empty commits cause repeated confusion.

### 2. Pre-edit sync strategy

**Score:** 3/10 (Cross-cutting +1, Repeated pattern +2)

**Notes:** Always merge/rebase before editing to avoid conflicts. Session impl-660b8210 did this correctly (merged 12 commits first). Standard git hygiene, but worth documenting as an explicit pattern for agent workflows.

### 3. Implementation artifact cleanup timing

**Score:** 3/10 (Cross-cutting +1, Destructive potential +2)

**Notes:** `.impl` directories must be cleaned before squashing. Could be promoted to full tripwire if automated workflows don't handle cleanup, but may be addressed by making `clear_impl_context` a standard post-implementation step.

## Cornerstone Redirect

One item belongs in code rather than documentation:

### resolve-review-threads error message improvement

**Current state:** Error message "Item at index 0 is not an object" is generic.

**Recommendation:** Improve error message in `src/erk/exec_scripts/resolve_review_threads.py` to include expected format: "Expected object with 'thread_id' key, got string. Format: [{\"thread_id\": \"...\"}]"

**Rationale:** Schema enforcement belongs in code. Documentation created above (exec-script-reference.md) is still valuable as a reference, but a clearer error message would prevent the trial-and-error that occurred in two sessions.

This is a code change suggestion, not a documentation item. The implementing agent should consider adding this improvement alongside the documentation updates.
