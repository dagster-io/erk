# Documentation Plan: Fix release process documentation with explicit git commands and troubleshooting guide

## Context

This PR (PR #7832) fixes critical documentation in `RELEASING.md` that caused errors during the erk 0.8.0 release. The original Step 9 merge instructions used a one-liner that referenced a non-existent script (`.erk/bin/activate.sh`) and incorrectly implied that the activate script would switch git branches. When an engineer followed these instructions, the release process failed because they ended up on the wrong branch.

The PR replaces the problematic one-liner with explicit git commands, adds a warning about what the activate script does NOT do, and adds a Troubleshooting section documenting two gotchas discovered during the release: (1) slash-based branch names cause Graphite ref conflicts, and (2) the activate script does not switch branches. These learnings need to be propagated to docs/learned/ for future discoverability by agents and developers.

The key value of this learn plan is extracting the institutional knowledge gained from the 0.8.0 release failure into discoverable documentation. The PR itself fixes the authoritative documentation, but the lessons learned about Graphite branch naming, activate script behavior, and command verification patterns should be captured in docs/learned/ where agents will find them when working on related tasks.

## Raw Materials

See associated PR #7832 and session e0134858-1a73-4e80-b8ee-905be44820a4.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 5     |
| Contradictions to resolve      | 0 (RESOLVED by PR) |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 1     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring cleanup:

### 1. Phantom release-process.md Reference

**Location:** `docs/learned/erk-dev/index.md`
**Action:** CREATE_FILE (recommended) or DELETE_REFERENCE
**Phantom References:** `release-process.md` (file does not exist)
**Cleanup Instructions:** The index.md references `release-process.md` with read_when guidance "releasing a new version of erk, creating version tags, understanding the erk release workflow". This file should be created with the 0.8.0 release learnings. This is the recommended action vs. deleting the reference, since the learnings from this PR are perfect content for it.

## Documentation Items

### HIGH Priority

#### 1. Silent `erk pr submit` Verification Tripwire

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session e0134858

**Draft Content:**

```markdown
**running erk pr submit with no visible output** → Verify PR creation with `gh pr view --json url -q '.url'` or `gh pr list --head "$(git branch --show-current)"`. Silent success requires explicit verification; the command may complete without any stdout/stderr confirmation.
```

This tripwire addresses a non-obvious failure mode where `erk pr submit` can succeed but produce no output, leaving the user uncertain whether the PR was created. The session showed the implementer using `gh pr view` as a fallback to confirm PR existence.

#### 2. Create Release Process Learnings Document

**Location:** `docs/learned/erk-dev/release-process.md`
**Action:** CREATE
**Source:** [PR #7832] RELEASING.md changes + session analysis

**Draft Content:**

```markdown
---
title: Release Process Learnings
read_when:
  - "releasing a new version of erk"
  - "creating version tags"
  - "understanding the erk release workflow"
  - "debugging release merge failures"
tripwires:
  - action: "using activate script for branch switching"
    warning: "The activate script only sets up venv and working directory. It does NOT change git branches. Use explicit `git checkout <branch>` commands."
  - action: "creating branch names with slashes for releases"
    warning: "Avoid slash-based branch names (e.g., `release/X.Y.Z`) in erk. They cause Graphite `refs/gt-fetch-head` conflicts. Use hyphens instead: `release-X.Y.Z`."
---

# Release Process Learnings

Lessons learned from erk releases, particularly the 0.8.0 release.

## Common Pitfalls

### Branch Naming Convention

Use hyphen-based release branch names (`release-X.Y.Z`), not slash-based names (`release/X.Y.Z`). Slash-based names cause Graphite `refs/gt-fetch-head` conflicts during stack operations.

### Activate Script Limitations

The workspace activation script (sourced during worktree entry) sets up:
- Virtual environment
- Working directory
- Environment variables from `.env`
- Shell completions

It does NOT:
- Change git branches
- Perform git operations

Always use explicit `git checkout` commands for branch switching.

## Step 9 Merge Sequence

See RELEASING.md for the authoritative sequence. Key points:
- Capture current branch BEFORE switching: `RELEASE_BRANCH=$(git branch --show-current)`
- Explicitly checkout master: `git checkout master`
- Pull latest: `git pull origin master`
- Merge with no-edit: `git merge "$RELEASE_BRANCH" --no-edit`
- Push with tags: `git push origin master --tags`

## Related Documentation

- [RELEASING.md](../../../RELEASING.md) - Authoritative release process
- [Workspace Activation](../erk/workspace-activation.md) - Activate script details
- [Git and Graphite Edge Cases](../architecture/git-graphite-quirks.md) - Graphite quirks
```

### MEDIUM Priority

#### 3. Graphite Branch Naming Convention

**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** [PR #7832] RELEASING.md Troubleshooting section (lines 115-123)

**Draft Content:**

Add a new section after the existing content:

```markdown
## Branch Naming and Ref Conflicts

**Surprising Behavior**: Branch names containing slashes (e.g., `release/X.Y.Z`) can cause Graphite `refs/gt-fetch-head` conflicts during stack operations. This manifests as mysterious ref errors when running gt commands.

**Why It's Surprising**: Git allows slashes in branch names freely, but Graphite's internal ref tracking creates paths that conflict with slash-based names.

**Solution**: Use hyphen-based branch names instead of slashes:

| Pattern | Example | Status |
|---------|---------|--------|
| Slash-based | `release/0.8.0` | Avoid - causes ref conflicts |
| Hyphen-based | `release-0.8.0` | Preferred |

This applies to release branches and any other branches that might use directory-style naming.

**Discovery Context**: Encountered during erk 0.8.0 release. The `release/0.8.0` branch caused Graphite errors that were resolved by using `release-0.8.0` naming.

**Location in Codebase**: Project convention; see RELEASING.md Troubleshooting section.
```

#### 4. Activate Script Branch Behavior Clarification

**Location:** `docs/learned/erk/workspace-activation.md`
**Action:** UPDATE
**Source:** [PR #7832] RELEASING.md line 111 warning + session analysis

**Draft Content:**

Add a new section after "Activation Script Structure":

```markdown
## What Activation Does NOT Do

The activation script is limited to workspace setup. It does NOT perform git operations:

- **Does NOT change branches** - You must use `git checkout` explicitly
- **Does NOT pull or fetch** - Repository state is unchanged
- **Does NOT merge or rebase** - Branch relationships are unchanged

A common misconception is that sourcing the activation script will "switch" to the worktree's branch. This is incorrect. The script changes your shell's working directory and sets up the environment, but git operations must be performed separately.

### Example: Releasing to Master

When merging a release branch to master, do NOT assume activate.sh handles branching:

```bash
# WRONG - activate.sh doesn't switch branches
source .erk/bin/activate.sh && git merge "$RELEASE_BRANCH"

# CORRECT - explicit git commands
RELEASE_BRANCH=$(git branch --show-current)
git checkout master
git pull origin master
git merge "$RELEASE_BRANCH" --no-edit
```

See RELEASING.md Step 9 for the complete release merge sequence.
```

### LOW Priority

#### 5. Documentation Changes Require Full CI

**Location:** `docs/learned/ci/ci-behavior.md` or `docs/learned/testing/testing.md`
**Action:** UPDATE (if file exists) or SKIP
**Source:** [Impl] Session e0134858 pattern observation

**Draft Content:**

This is a minor observation: even documentation-only changes to files like RELEASING.md run the full CI test suite (5349 + 136 + 126 tests) for formatting, linting, and integration verification. This is expected behavior and ensures documentation changes don't break formatting rules or accidentally include problematic content.

**Recommendation:** This may not warrant a separate documentation entry. The behavior is standard CI discipline and low-impact. Consider SKIP unless there's a specific location where agents would benefit from this context.

## Contradiction Resolutions

### 1. Misleading activate.sh One-Liner (RESOLVED by PR)

**Status:** RESOLVED - PR #7832 fixes this contradiction

**Existing doc:** RELEASING.md (pre-PR state)
**Conflict:** The old Step 9 used a one-liner `source .erk/bin/activate.sh && git merge "$RELEASE_BRANCH"` that implied the activate script would set up the correct branch context. Additionally, the referenced file `.erk/bin/activate.sh` does not exist (phantom reference).
**Resolution:** PR replaces the problematic one-liner with explicit git commands and adds a warning note. No additional action needed beyond what the PR already provides.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent Command Verification Pattern

**What happened:** `erk pr submit` completed successfully but produced no stdout/stderr output, leaving uncertainty about whether the PR was created.
**Root cause:** Command design doesn't provide confirmation output on success.
**Prevention:** Always follow up with verification command (`gh pr view --json url -q '.url'`) when output is unexpectedly empty.
**Recommendation:** TRIPWIRE - Added to pr-operations/tripwires.md (HIGH priority item #1)

### 2. Phantom File Reference

**What happened:** RELEASING.md referenced `.erk/bin/activate.sh` which does not exist.
**Root cause:** Documentation was not validated against actual file system state.
**Prevention:** When referencing scripts or files in documentation, verify they exist. Use source pointers to existing files, not assumed paths.
**Recommendation:** ADD_TO_DOC - The release-process.md document (item #2) includes guidance on explicit git commands instead of script references.

### 3. Incorrect Branch Switching Assumption

**What happened:** The documentation implied that activate.sh would handle branch context, leading to attempting git merge on the wrong branch.
**Root cause:** Misconception about what the activation script does.
**Prevention:** Document what tools do NOT do, not just what they do. Add explicit "What X Does NOT Do" sections.
**Recommendation:** TRIPWIRE - Added to erk-dev/release-process.md and erk/workspace-activation.md

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. `erk pr submit` Silent Success

**Score:** 6/10 (Non-obvious +2, Silent failure +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** After running `erk pr submit` with no output
**Warning:** "If no output appears, verify PR creation with `gh pr view --json url -q '.url'` or `gh pr list --head \"$(git branch --show-current)\"`. Silent success requires explicit verification."
**Target doc:** `docs/learned/pr-operations/tripwires.md`

This tripwire addresses a non-obvious failure mode discovered during implementation. The command can succeed but produce no confirmation output, which is especially problematic for agents that rely on command output to determine success. The session showed the implementer correctly falling back to `gh pr view` for verification, demonstrating this is a repeatable pattern worth codifying.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Documentation Changes Require Full CI

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** While it's non-obvious that pure markdown changes trigger the full test suite (5349+ tests), this is standard CI practice and low-severity if misunderstood. The worst case is surprise at CI duration, not actual errors. Documentation in ci/ or testing/ may be sufficient without tripwire status. If agents repeatedly show confusion about CI timing for docs changes, this could be promoted to tripwire status.

## Implementation Order

1. **First:** Create `docs/learned/erk-dev/release-process.md` - resolves the phantom reference in index.md AND captures the core learnings from this PR
2. **Second:** Add tripwire for `erk pr submit` silent success to `docs/learned/pr-operations/tripwires.md`
3. **Third:** Update `docs/learned/architecture/git-graphite-quirks.md` with branch naming convention section
4. **Fourth:** Update `docs/learned/erk/workspace-activation.md` with "What Activation Does NOT Do" section
5. **Optional:** Consider whether documentation CI note warrants addition to testing docs

## Completeness Check

- All 3 items from DiffAnalyzer inventory: ADDRESSED
  - Step 9 fixes: Captured in release-process.md
  - Warning about activate.sh: Captured in workspace-activation.md update
  - Troubleshooting section: Captured in git-graphite-quirks.md and release-process.md
- All session patterns evaluated: YES
- Phantom reference resolved: YES (create release-process.md)
- Contradiction resolved: YES (by PR itself)
