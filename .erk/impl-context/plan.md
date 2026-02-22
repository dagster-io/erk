# Documentation Plan: Rename session branch prefix to async-learn

## Context

This plan addresses documentation gaps created by PR #7802, which renamed the session upload branch prefix from `session/` to `async-learn/`. While the code change itself was a straightforward string replacement across 6 files (+19/-19 lines), it introduces a third branch type in erk's taxonomy that was previously undocumented. The existing branch naming documentation covers issue-based (`P{issue}-`) and draft-PR (`planned/`) branches, but session upload branches for the async learn workflow were never formally documented.

The rename improves discoverability: `async-learn/{plan_id}` immediately signals the branch's purpose in the async learn workflow, whereas `session/{plan_id}` was ambiguous. This architectural significance means the change warrants documentation beyond just updating help text examples. Future agents working with session uploads, async learn workflows, or branch naming conventions need to understand this third branch type and its lifecycle.

Additionally, the implementation session revealed a partial preprocessing edge case: when `.erk/impl-context/` exists but contains only PR comments (no session XMLs), the agent must supplement with local session preprocessing. This hybrid behavior was not previously documented and warrants a tripwire to prevent confusion.

## Raw Materials

PR #7802: https://github.com/schrockn/erk/pull/7802

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 5     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. Session Upload Branch Pattern Documentation

**Location:** `docs/learned/sessions/session-upload-branches.md`
**Action:** CREATE
**Source:** [PR #7802]

**Draft Content:**

```markdown
---
title: Session Upload Branch Pattern
read_when:
  - working with remote session uploads
  - debugging session discovery in CI
  - understanding async learn material flow
  - seeing references to async-learn/ branches
  - implementing or modifying upload-session command
tripwires:
  - action: "assuming all erk branches follow P{issue}- or planned/ pattern"
    warning: "Session upload branches use async-learn/{plan_id} format. See this doc for the third branch type."
---

# Session Upload Branch Pattern

Session upload branches provide git-based storage for Claude Code session files, enabling the async learn pipeline to consume session data from remote contexts.

## Branch Format

**Pattern:** `async-learn/{plan_id}`

**Examples:**
- `async-learn/123` (sessions for plan #123)
- `async-learn/7802` (sessions for plan #7802)

## Purpose and Lifecycle

Session upload branches serve a specific purpose: storing session JSONL files in git for consumption by the async learn GitHub Actions workflow.

**Creation:** `erk exec upload-session` creates the branch from `origin/master`, not from the plan implementation branch. See `src/erk/cli/commands/exec/scripts/upload_session.py` for the implementation.

**Storage location:** Sessions are stored at `.erk/session/{session_id}.jsonl` on the branch.

**Idempotency:** Branches are force-pushed on each upload. The branch content is replaced, not appended.

**Download:** `erk exec download-remote-session --session-branch async-learn/{plan_id}` fetches sessions from these branches. See `src/erk/cli/commands/exec/scripts/download_remote_session.py`.

**Cleanup:** After async learn materials are processed, branches are cleaned up. See the cleanup comment in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`.

## Distinction from Other Branch Types

Erk manages three distinct branch naming conventions:

| Branch Type | Format | Purpose |
|-------------|--------|---------|
| Issue-based plans | `P{issue}-{slug}-{timestamp}` | Plan implementation worktrees |
| Draft-PR plans | `planned/{slug}-{timestamp}` | Draft-PR plan worktrees |
| Session uploads | `async-learn/{plan_id}` | Remote session storage for async learn |

Session upload branches differ from implementation branches in several ways:
- No timestamp suffix (reuses same branch name per plan)
- Force-push enabled (content is replaced, not versioned)
- Created from `origin/master` (not related to implementation branch)
- Contains only session files, not implementation code

## Breaking Change Note

PR #7802 renamed the prefix from `session/` to `async-learn/`. Any existing branches using the old `session/{plan_id}` format will not be found by current code.

## Related Documentation

- [Branch Naming Conventions](../erk/branch-naming.md) - All erk branch naming patterns
- [Session File Lifecycle](lifecycle.md) - Session storage tiers and persistence
- [Async Learn Local Preprocessing](../planning/async-learn-local-preprocessing.md) - How sessions are preprocessed before upload
```

---

#### 2. Branch Naming Taxonomy Update

**Location:** `docs/learned/erk/branch-naming.md`
**Action:** UPDATE
**Source:** [PR #7802]

**Draft Content:**

Add the following section after the existing "Draft-PR Branches" section:

```markdown
### Session Upload Branches

**Format:** `async-learn/{plan_id}`

**Examples:**
- `async-learn/123` (session uploads for plan #123)

Session upload branches are created by `erk exec upload-session` to store Claude Code session JSONL files in git for remote consumption by the async learn pipeline. They are force-pushed on each upload for idempotency.

**Constraints:**
- No timestamp suffix (reuses same branch name per plan)
- Force-push enabled (branch content is replaced, not appended)
- Created from origin/master (not plan implementation branch)

**Storage location:**
- Sessions stored at `.erk/session/{session_id}.jsonl` on the branch

**See:** [Session Upload Branch Pattern](../sessions/session-upload-branches.md) for complete lifecycle documentation.
```

Also update the Related Topics section to add:
```markdown
- [Session Upload Branch Pattern](../sessions/session-upload-branches.md) - Git-based session storage for async learn workflow
```

---

#### 3. Hybrid Preprocessing Pattern Documentation

**Location:** `docs/learned/planning/async-learn-local-preprocessing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add the following section after "Preprocessing Pipeline Internals":

```markdown
## Partial Preprocessing Handling

When `.erk/impl-context/` exists from CI preprocessing but contains incomplete materials, the learn workflow must detect and supplement the missing data.

**Detection:** Check whether `.erk/impl-context/` contains both PR comment files AND session XML files. Partial preprocessing occurs when only one type is present.

**Typical partial case:** CI commits PR comments but session XMLs were not preprocessed (e.g., session files were unavailable during the CI run).

**Fallback behavior:** When session XMLs are missing:
1. Run `erk exec get-learn-sessions` to discover session files
2. Preprocess missing sessions locally
3. Combine with existing preprocessed PR comments

**Why this matters:** The presence of `.erk/impl-context/` directory alone does not guarantee complete materials. Always validate contents before assuming preprocessing is complete.
```

Also add this tripwire to the frontmatter:
```yaml
  - action: "assuming .erk/impl-context/ contains all preprocessed materials"
    warning: "Check for both PR comments AND session XMLs. Partial preprocessing requires fallback to local session discovery."
```

---

### MEDIUM Priority

#### 4. Session Lifecycle Cross-Reference

**Location:** `docs/learned/sessions/lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7802]

**Draft Content:**

In the "Why Gist-Based Persistence Exists" section, add the following paragraph:

```markdown
**Alternative: Git-based session storage.** For plans where git-based storage is preferred over gists, sessions can be uploaded to `async-learn/{plan_id}` branches via `erk exec upload-session`. This provides an alternative persistence path that doesn't require gist creation. See [Session Upload Branch Pattern](session-upload-branches.md) for details.
```

---

#### 5. Async Learn Remote Session Sources Update

**Location:** `docs/learned/planning/async-learn-local-preprocessing.md`
**Action:** UPDATE
**Source:** [PR #7802]

**Draft Content:**

In the "Why Local Preprocessing Exists" section (or create a new "Remote Session Sources" section), add:

```markdown
**Remote session sources:**
- **Gist-based:** Uploaded via `upload-learn-materials`, stored as GitHub gists
- **Git-based:** Uploaded via `upload-session` to `async-learn/{plan_id}` branches

The git-based approach (via `upload-session`) stores sessions directly in the repository as branch contents, which can be faster for CI contexts where git operations are already optimized. See [Session Upload Branch Pattern](../sessions/session-upload-branches.md) for the branch lifecycle.
```

---

## Contradiction Resolutions

No contradictions detected. The existing documentation correctly describes the two existing branch patterns (issue-based `P{issue}-` and draft-PR `planned/`). The session upload branch pattern was not previously documented, so there is nothing to contradict.

## Stale Documentation Cleanup

No stale documentation detected. All existing docs have valid file references.

## Prevention Insights

No errors or failed approaches were encountered during the implementation session. The rename proceeded smoothly with corresponding test updates.

## Tripwire Candidates

One item meets the tripwire-worthiness threshold:

### 1. Session Upload Branch Naming Convention

**Score:** 6/10
- Cross-cutting (+2): Affects multiple commands (`upload-session`, `download-remote-session`, `trigger-async-learn`)
- Non-obvious (+2): Branch naming convention not discoverable from code alone; requires understanding of async learn architecture
- External tool quirk (+1): Uses git branch mechanics for remote storage as an alternative to gists
- Repeated pattern (+1): Pattern appears in multiple exec scripts and their tests

**Trigger:** Before assuming all erk branches follow `P{issue}-` or `planned/` pattern

**Warning:** Session upload branches use `async-learn/{plan_id}` format. These branches are distinct from issue-based (`P{issue}-`) and draft-PR (`planned/`) branches.

**Target doc:** `docs/learned/sessions/tripwires.md`

This is tripwire-worthy because agents working with branch naming or async learn workflows need to know about all three branch types. The `async-learn/` prefix is non-obvious and easily confused with the two more common patterns. Without this tripwire, an agent might incorrectly assume all erk branches use the `P{issue}-` format and fail to find session upload branches.

The second tripwire candidate is for partial preprocessing detection:

**Trigger:** Before assuming `.erk/impl-context/` contains all preprocessed materials

**Warning:** Check for both PR comments AND session XMLs. Partial preprocessing requires fallback to local session discovery. See docs/learned/planning/async-learn-local-preprocessing.md.

**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire prevents agents from skipping session discovery when `.erk/impl-context/` exists but is incomplete.

## Potential Tripwires

None identified. Both tripwire candidates meet the score threshold.

## Implementation Order

1. **FIRST:** Create `docs/learned/sessions/session-upload-branches.md` (establishes core concept)
2. **SECOND:** Update `docs/learned/erk/branch-naming.md` (adds third branch category)
3. **THIRD:** Update `docs/learned/planning/async-learn-local-preprocessing.md` (adds hybrid preprocessing + remote sources)
4. **FOURTH:** Update `docs/learned/sessions/lifecycle.md` (adds cross-reference)
5. **FIFTH:** Add tripwires to `docs/learned/sessions/tripwires.md` and `docs/learned/planning/tripwires.md` (via `erk docs sync` after frontmatter updates)

## Source Pointers for Verification

When implementing this plan, use these grep patterns to verify accuracy:

1. **Session upload branch format:**
   - File: `src/erk/cli/commands/exec/scripts/upload_session.py`
   - Grep: `async-learn/{plan_id}` or `session_branch`

2. **Download command:**
   - File: `src/erk/cli/commands/exec/scripts/download_remote_session.py`
   - Grep: `--session-branch` or `async-learn/`

3. **Cleanup references:**
   - File: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`
   - Grep: "Clean up async-learn branches"

4. **Test validation:**
   - Files: `tests/unit/cli/commands/exec/scripts/test_upload_session.py`
   - Grep: `async-learn/` to verify naming convention tests
