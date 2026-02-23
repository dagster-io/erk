# Documentation Plan: Extract and update PR titles in ci-update-pr-body

## Context

This implementation plan (#7936) addressed a bug where the `/erk:git-pr-push` workflow was generating incorrect PR titles based on session context rather than Claude's commit message output. The fix modified the `ci-update-pr-body` exec script to extract the PR title from Claude's generated commit message (first line = title, remainder = body) and update both title and body via the `update_pr_title_and_body()` gateway method.

The implementation session revealed several important patterns beyond the core feature. First, rebase operations during implementation can cause Graphite tracking to diverge, requiring `gt track --no-interactive` before PR submission. Second, when bot review comments flag code that was removed in a recently-landed PR, the correct resolution is rebasing onto fresh master rather than fixing code style issues. Third, understanding the difference between GitHub's PR diff (based on merge base) and local git diff (based on master tip) is essential for diagnosing stale review feedback.

Future agents implementing exec scripts that parse Claude output, handling PR submission after rebase operations, or addressing automated review comments will benefit from the patterns documented here. The title extraction algorithm is reusable across other exec scripts that receive multiline Claude output.

## Raw Materials

PR #7936

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 14    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. ci-update-pr-body Implementation Architecture

**Location:** `docs/learned/cli/ci-update-pr-body-implementation.md`
**Action:** CREATE
**Source:** [Impl] [PR #7936]

**Draft Content:**

```markdown
---
read-when:
  - modifying ci-update-pr-body exec script
  - implementing title extraction in exec scripts
  - working with PR metadata synchronization
tripwires: 1
---

# ci-update-pr-body Implementation

This exec script generates and updates both PR title and body based on Claude's commit message output.

## Core Behavior

The script performs dual updates: extracting the title from Claude's commit message (first line) and the body (remaining lines), then calling `update_pr_title_and_body()` for synchronized metadata updates.

## Title Extraction

Title parsing uses a simple algorithm: split on first newline, first line becomes title, remainder becomes body. For single-line input, body is empty.

See `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` for `_parse_title_and_summary()` implementation.

## Gateway Method Selection

Use `update_pr_title_and_body()` when both fields need updating (synchronized PR metadata). Use `update_pr_body()` only for body-only updates in legacy contexts.

## JSON Output Schema

Success response includes `title` field for observability:
- `{"success": true, "pr_number": int, "title": str}`

## Commit Message Format Dependency

Title extraction depends on commit message prompt format where line 1 = title. Cross-reference: `packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md`
```

---

#### 2. Graphite Divergence After Rebase (Tripwire)

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

This tripwire addresses a common failure mode when using `erk pr submit` after rebase operations. The root cause is that rebase rewrites history, breaking Graphite's internal tracking metadata. Without re-tracking, `gt submit` fails with "diverged branch" error.

The trigger condition is: Before running `erk pr submit` after any rebase operation.

The warning message should be: "After rebase, Graphite tracking may diverge. If `gt submit` fails with 'diverged branch', run `gt track --no-interactive <branch>` then retry."

This pattern has high severity (score 6/10) because it is non-obvious (most developers don't understand Graphite's internal tracking), cross-cutting (affects all PR submission workflows), and has destructive potential (failed submission requires manual recovery).

---

#### 3. Stale Merge Base Detection Workflow (Tripwire)

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

When automated review bots flag code style issues on files that shouldn't be in the PR, the root cause is often a stale merge base. The bot sees files based on GitHub's PR diff (computed from merge base), which may include code that was removed in PRs that landed after the branch was created.

The trigger condition is: Before addressing automated review comments that flag removed features.

The warning message should be: "Check merge base distance: `git log --oneline $(git merge-base master HEAD)..origin/master | wc -l`. If >10 commits behind, rebase onto latest master before making code changes. Bot may be flagging code that was removed in a later PR."

This has high severity (score 6/10) because it is non-obvious, cross-cutting, and causes silent failure (agent wastes effort fixing code that shouldn't exist).

---

#### 4. Non-Fast-Forward Push During Impl-Context Cleanup (Tripwire)

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

During `.erk/impl-context/` cleanup, git push may fail with non-fast-forward rejection because CI/workflow updates added commits to the remote branch.

The trigger condition is: When `.erk/impl-context/` cleanup fails with non-fast-forward rejection.

The warning message should be: "Remote branch may have additional commits from CI/workflow updates. Run `git pull --rebase origin $(git branch --show-current)` before retrying cleanup. Alternative: use `git push --force-with-lease` after verifying local commit is safe."

Score 4/10: Cross-cutting, external tool quirk, repeated pattern.

---

### MEDIUM Priority

#### 1. Force Push Workflow After Rebase

**Location:** `docs/learned/pr-operations/rebase-workflows.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - performing rebase operations on pushed branches
  - handling diverged branch errors
  - force pushing after history rewrite
tripwires: 1
---

# Rebase Workflows and Force Push

## When Force Push is Needed

After rebase operations that rewrite history, the local branch diverges from remote. Regular push fails with non-fast-forward rejection.

## Safe Force Push Pattern

Always use `--force-with-lease` (never `--force`):
- Verifies no one else pushed to the branch
- Fails safely if remote has unexpected commits

## Verification Steps

1. Check `git status` for divergence warnings before push
2. After force push, verify `gh pr diff --name-only` matches expectations
3. If Graphite tracking diverged, use `gt track --no-interactive`

## Rebase Artifact Cleanup

When a feature was removed in master but branch commits re-add it:
- Pattern: Rebasing may skip removal commits but preserve additions
- Detection: Bot flags code from removal PR that already landed
- Resolution: Manual rebase onto fresh master (not automatic conflict resolution)
- Warning signs: "warning: skipped previously applied commit" during rebase
```

---

#### 2. PR Diff Diagnostics

**Location:** `docs/learned/pr-operations/pr-diff-diagnostics.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - GitHub PR diff shows unexpected files
  - bot reviews flag code that doesn't exist locally
  - diagnosing diff discrepancies in review workflows
---

# PR Diff Diagnostics

## Two Views of the Same Branch

GitHub and local git can show different diffs:

- **GitHub view**: `gh pr diff` (based on PR merge base)
- **Local view**: `git diff master` (based on current master tip)

## When Views Diverge

Divergence occurs when the PR's merge base is stale (master has moved forward).

## Diagnosis Commands

Compare merge base to master tip:
- `git merge-base master HEAD` - shows PR's merge base commit
- `git rev-parse origin/master` - shows current master tip
- `git log --oneline $(git merge-base master HEAD)..origin/master | wc -l` - counts commits behind

## Three-Dot vs Two-Dot Diff

- `git diff master...HEAD` (three dots): Compares against merge base (what GitHub shows)
- `git diff master` (two dots): Compares against master tip (current local state)

## Resolution

When merge base is stale (>10 commits behind), rebase onto latest master. Verify both views converge after force push.
```

---

#### 3. Commit Message Parsing Pattern

**Location:** `docs/learned/architecture/commit-message-parsing-pattern.md`
**Action:** CREATE
**Source:** [Impl] [PR #7936]

**Draft Content:**

```markdown
---
read-when:
  - implementing exec scripts that parse Claude output
  - extracting title/body from multiline text
  - working with commit message formatting
---

# Commit Message Parsing Pattern

## The Pattern

Split multiline Claude output into title (first line) and body (remainder):

```python
def parse_title_and_body(content: str) -> tuple[str, str]:
    if "\n" in content:
        title, body = content.split("\n", 1)
        return title, body
    return content, ""
```

## Characteristics

- Handles single-line input (returns empty body)
- Uses `split("\n", 1)` to preserve multiline body content
- First line is always the title, no trimming applied

## Usage

See `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` for the canonical implementation.

## Dependency

This pattern depends on commit message prompts having first line = title format. Cross-reference: `packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md`
```

---

#### 4. GitHub API Method Selection Guide

**Location:** `docs/learned/architecture/pr-body-formatting.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7936]

Add a section comparing `update_pr_body()` vs `update_pr_title_and_body()`:

- When to use body-only: Legacy scripts, body-only updates
- When to use title+body: PR creation, synchronized updates, `ci-update-pr-body`
- BodyText vs String: BodyText wrapper for inline content, BodyFile for file-based content

---

#### 5. Exec Script JSON Output Schemas

**Location:** `docs/learned/reference/exec-scripts-json-schemas.md`
**Action:** CREATE
**Source:** [Impl] [PR #7936]

**Draft Content:**

```markdown
---
read-when:
  - implementing new exec scripts
  - parsing exec script output
  - debugging CI workflow failures
---

# Exec Script JSON Output Schemas

Reference for JSON schemas returned by exec scripts.

## ci-update-pr-body

**Success:**
```json
{"success": true, "pr_number": 123, "title": "PR title text"}
```

**Error:**
```json
{"success": false, "error": "Error message", "pr_number": 123}
```

Note: `title` field added in plan #7936. This is a breaking change for callers expecting the old schema.

## Other Scripts

(Add schemas for other exec scripts as they are documented)
```

---

#### 6. Review Stale Code Resolution Pattern

**Location:** `docs/learned/reviews/stale-code-resolution-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - resolving bot comments on rebased-away code
  - handling review threads that flag removed features
---

# Stale Code Resolution Pattern

## When to Use

Bot flags violations on code that was removed by a subsequent rebase onto master.

## Standard Resolution Comment

"Resolved - stale code removed by rebase onto master. Reference: PR #XXXX removed this feature."

## Batch Resolution

Use `erk exec resolve-review-threads` with JSON array for efficient bulk operations.

## Handling Duplicates

GitHub may duplicate threads during force-push. Resolve both active and outdated versions.
```

---

#### 7. Force Push After Rebase (Tripwire)

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

The trigger condition is: After rebasing a branch that has been pushed to remote.

The warning message should be: "Expect non-fast-forward push rejection. Use `git push --force-with-lease` (never `--force`). Verify `gh pr diff --name-only` matches expectations after force push."

Score 4/10: Cross-cutting, external tool quirk, repeated pattern.

---

### LOW Priority

#### 1. Draft PR Lifecycle with Title Updates

**Location:** `docs/learned/planning/draft-pr-lifecycle.md`
**Action:** UPDATE (if exists) or CREATE
**Source:** [PR #7936]

Add note that draft PRs now receive title+body updates (previously body-only). Metadata prefix preserved in body, title extracted from commit message first line.

---

#### 2. Git Diff Mode Comparison

**Location:** `docs/learned/reference/git-workflows.md`
**Action:** UPDATE
**Source:** [Impl]

Add comparison table:
- `git diff master...HEAD` (three dots): Compares against merge base
- `git diff master` (two dots): Compares against master tip
- Use cases: Three-dot for "what PR changed", two-dot for "current state vs master"

---

#### 3. BodyText Wrapper Usage

**Location:** `docs/learned/architecture/pr-body-formatting.md`
**Action:** UPDATE
**Source:** [Impl]

Add section explaining BodyText vs raw string:
- BodyText: Wrapper for inline body content
- BodyFile: For file-based content
- When to use: `update_pr_title_and_body()` requires BodyContent type

---

## Contradiction Resolutions

No true contradictions found. The gap analysis flagged one potential conflict regarding `ci-update-pr-body` environment requirements documentation, but this was classified as STALE_NOT_CONTRADICTION - both interpretations (Claude generates output, script parses it) are correct in context. The existing documentation accurately describes that the script uses `require_prompt_executor()` to call Claude, and the new title extraction happens AFTER Claude generates output via the `_parse_output()` method.

## Stale Documentation Cleanup

No stale documentation identified. All code references in existing documentation were verified as current with no phantom references found.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Non-Fast-Forward Push During Impl-Context Cleanup

**What happened:** Git push rejected with non-fast-forward error during `.erk/impl-context/` removal.

**Root cause:** Remote branch had additional commits from CI/workflow updates that ran after the local commit was made.

**Prevention:** Always pull-rebase before pushing in the `.erk/impl-context/` cleanup step. Alternative: use `git push --force-with-lease` after verifying local commit is safe to overwrite.

**Recommendation:** TRIPWIRE

---

### 2. Graphite Divergence After Rebase

**What happened:** `gt submit` failed with "diverged branch" error after earlier rebase operation.

**Root cause:** Rebase rewrites commit history, breaking Graphite's internal tracking metadata. Graphite no longer recognizes the branch as tracking the expected remote.

**Prevention:** After any rebase operation, immediately re-track affected branches with `gt track --no-interactive <branch>` before attempting `gt submit`.

**Recommendation:** TRIPWIRE

---

### 3. Bot Reviews Flagging Removed Feature Code

**What happened:** Automated review bot flagged 3 code style issues in `github_admin/` files that had been removed in PR #7947.

**Root cause:** Branch's merge base was 19 commits behind master. The rebase had preserved commits that added back code that was subsequently removed in master. GitHub's PR diff (based on stale merge base) still showed these files.

**Prevention:** Before addressing bot comments, verify merge base is current. If >10 commits behind, rebase onto fresh master first. Do not fix code style issues on code that shouldn't exist in the PR.

**Recommendation:** TRIPWIRE

---

### 4. Force Push Required After Rebase

**What happened:** After rebasing, `git push` failed with non-fast-forward rejection because local and remote branches diverged.

**Root cause:** Rebase rewrites history, creating new commit SHAs. The remote still has the old commits.

**Prevention:** Expect to use `git push --force-with-lease` after rebase operations. This is normal workflow, not an error condition. Check `git status` for divergence warnings before pushing.

**Recommendation:** ADD_TO_DOC (include in rebase-workflows.md)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Graphite Divergence After Rebase

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before running `erk pr submit` after any rebase operation
**Warning:** After rebase, Graphite tracking may diverge. If `gt submit` fails with 'diverged branch', run `gt track --no-interactive <branch>` then retry.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because agents frequently perform rebase operations (to sync with master, to fix conflicts, to clean up commits) and the Graphite divergence is completely non-obvious. There's no indication during the rebase that Graphite tracking will break. The error message from `gt submit` is confusing and the recovery path requires knowing about `gt track --no-interactive`, which is an obscure command.

### 2. Stale Merge Base Detection

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before addressing automated review comments that flag removed features
**Warning:** Check merge base distance: `git log --oneline $(git merge-base master HEAD)..origin/master | wc -l`. If >10 commits behind, rebase onto latest master before making code changes. Bot may be flagging code that was removed in a later PR.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

This pattern caused significant wasted effort in the implementation session. The agent prepared to fix code style issues on code that shouldn't exist at all. Without this tripwire, agents will continue making code changes to perpetuate removed features instead of rebasing to eliminate them.

### 3. Non-Fast-Forward Push During Impl-Context Cleanup

**Score:** 4/10 (Cross-cutting +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** When `.erk/impl-context/` cleanup fails with non-fast-forward rejection
**Warning:** Remote branch may have additional commits from CI/workflow updates. Run `git pull --rebase origin $(git branch --show-current)` before retrying cleanup. Alternative: use `git push --force-with-lease` after verifying local commit is safe.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because impl-context cleanup happens at the end of implementation sessions when agents are wrapping up, and the error is confusing because the agent doesn't expect other commits on the branch.

### 4. Force Push After Rebase

**Score:** 4/10 (Cross-cutting +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** After rebasing a branch that has been pushed to remote
**Warning:** Expect non-fast-forward push rejection. Use `git push --force-with-lease` (never `--force`). Verify `gh pr diff --name-only` matches expectations after force push.
**Target doc:** `docs/learned/pr-operations/tripwires.md` or `docs/learned/pr-operations/rebase-workflows.md`

This documents expected workflow rather than a sharp edge, but agents repeatedly encounter this and benefit from the reminder to use `--force-with-lease` specifically.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. GitHub PR Diff vs Local Git Diff Divergence

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Useful diagnostic pattern for understanding why GitHub shows different files than local diff. Not destructive - just confusing. Better documented as a reference pattern than as a tripwire warning. Could be promoted if agents repeatedly waste time on this confusion.

### 2. Rebase Artifact Cleanup

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Workflow pattern for handling commits that re-add removed features during rebase. This is a complex scenario that requires understanding git's rebase conflict resolution. Better documented as a workflow guide than as a tripwire. Could be promoted if the stale merge base tripwire doesn't catch this case upstream.

### 3. Long Test Data Line Formatting

**Score:** 2/10 (Repeated pattern +1, External tool quirk +1)
**Notes:** Multi-line format for test data to avoid E501 violations. This is covered by ruff configuration and standard code formatting practices. Not tripwire-worthy - agents should just follow formatting guidance from linters.
