# Documentation Plan: Fix TUI dispatch command: correct CLI path and update user-facing labels

## Context

PR #8213 fixed a broken TUI command that was calling a non-existent CLI path (`erk plan submit`) when it should have been calling the actual command (`erk pr dispatch`). The TUI's "Submit to Queue" functionality was invoking a path that did not exist, causing silent failure for users attempting to dispatch plans for remote AI implementation.

Beyond the code fix itself, this PR revealed a documentation contradiction: `docs/learned/cli/command-organization.md` documented `erk plan submit` as the submission command, when the actual CLI implementation is `erk pr dispatch`. The code was fixed to match reality, but the documentation still claims the wrong command exists. Additionally, an automated review bot (audit-pr-docs) caught a pre-existing inaccuracy in the status indicators documentation unrelated to the PR changes themselves.

The session demonstrated several effective patterns worth capturing: efficient reuse of recent classifier results, proper handling of outdated review threads, and proactive consistency maintenance when updating documentation tables. These patterns can help future agents working on similar PR operations.

## Raw Materials

See associated gist in the learn issue for session logs and analysis files.

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 5 |
| Contradictions to resolve | 1 |
| Tripwire candidates (score>=4) | 0 |
| Potential tripwires (score 2-3) | 1 |

## Contradiction Resolutions

### 1. Command Naming: `erk plan submit` vs `erk pr dispatch`

**Existing doc:** `docs/learned/cli/command-organization.md`
**Conflict:** Lines 59-66 describe `erk plan submit` as the plan submission command under the `erk plan` group, but this command does not exist. The actual command is `erk pr dispatch` (implemented at `src/erk/cli/commands/pr/dispatch_cmd.py`).
**Resolution:** Update the documentation to replace all references to `erk plan submit` with `erk pr dispatch`. The PR fixed the TUI code to call the correct command; now the documentation must match.

## Documentation Items

### HIGH Priority

#### 1. Correct command name in CLI organization doc

**Location:** `docs/learned/cli/command-organization.md`
**Action:** UPDATE
**Source:** [PR #8213] + contradiction analysis

**Draft Content:**

```markdown
<!-- Update lines 59-66 -->
### `erk plan` Subcommands

Plan management operations are under the `erk plan` group:

| Subcommand | Description               |
| ---------- | ------------------------- |
| `list`     | List open plans           |
| `co`       | Check out a plan's branch |
| `check`    | Check plan status         |

Note: Plan dispatch for remote execution is under `erk pr dispatch`, not `erk plan`.

<!-- Also update the "Plan Lifecycle" example section around line 335 -->
# Submit for execution
erk pr dispatch 42        # Queue for remote execution
```

The key changes:
1. Remove `submit` from the `erk plan` subcommands table
2. Add a note clarifying that dispatch is under `erk pr`
3. Update the "Plan Lifecycle" example to use `erk pr dispatch 42` instead of `erk plan submit 42`

#### 2. Fix status indicator blocking conditions

**Location:** `docs/learned/tui/status-indicators.md`
**Action:** UPDATE
**Source:** [PR #8213] (audit-pr-docs bot caught pre-existing inaccuracy)

**Draft Content:**

```markdown
<!-- Update line 67-68 in the indicator table -->
| 🚀    | Ready to merge    | Implemented stage when checks pass, no unresolved comments, no conflicts, not draft, no changes requested |
```

The current documentation is missing two conditions for the 🚀 indicator: the PR must not be in draft state and must not have changes requested. See `compute_status_indicators()` in lifecycle.py for the complete condition set. The `_non_blocking` set contains informational indicators; 🚀 is NOT in this set, meaning it IS affected by blocking conditions.

### MEDIUM Priority

#### 3. Classifier result caching guidance

**Location:** `docs/learned/pr-operations/addressing-feedback.md` (or create new section if this file doesn't exist)
**Action:** UPDATE or CREATE
**Source:** [Impl] (session-bc58a084-part1)

**Draft Content:**

```markdown
## Classifier Result Freshness

When `/erk:pr-preview-address` runs immediately before `/erk:pr-address` with no intervening code changes, agents may reuse the cached classifier results rather than re-running classification.

**When reuse is safe:**
- Preview just ran (within same session)
- No code changes between preview and address
- No new review comments added

**When fresh classification required:**
- Code changes made since preview
- Significant time elapsed
- New review threads appeared
- Different branch or PR

This is a pragmatic optimization. The `/erk:pr-address` command technically requires using the Task tool for Phase 1 classification, but re-running classification when results are seconds old provides no additional value.
```

#### 4. Outdated thread workflow

**Location:** `docs/learned/pr-operations/addressing-feedback.md`
**Action:** UPDATE
**Source:** [Impl] (session-bc58a084-part1)

**Draft Content:**

```markdown
## Handling Outdated Review Threads

When a review thread has `is_outdated: true` (line number is null because the code has changed), follow this workflow:

1. **Read the entire file** - Don't rely on line context; the code may have moved
2. **Search for relevant patterns** - Use grep to find where the discussed code might be now
3. **Verify issue status** - Determine if the issue still exists or was fixed by other changes
4. **Take appropriate action**:
   - If still broken: Fix and resolve the thread
   - If already fixed: Resolve with note explaining when/how it was addressed
   - If ambiguous: Ask clarifying question in thread

The key insight: outdated threads require whole-file context, not line-specific context.
```

#### 5. Documentation consistency maintenance

**Location:** `docs/learned/documentation/maintenance-checklist.md` (new file)
**Action:** CREATE
**Source:** [Impl] (session-bc58a084-part1)

**Draft Content:**

```markdown
---
title: Documentation Consistency Maintenance
read_when:
  - updating tables or lists in docs/learned
  - modifying frontmatter metadata
---

# Documentation Consistency Maintenance

When updating documentation, check for related artifacts that reference the same items.

## Cross-Reference Checklist

When adding to a table or list:
- [ ] Check frontmatter `tripwires` list for matching items
- [ ] Check `read_when` conditions if the item affects when to load the doc
- [ ] Check related docs in the same directory (e.g., tripwires.md)

## Example: Adding a New Emoji Indicator

When adding a new emoji to a status indicators table:
1. Add the row to the table with indicator logic
2. Update the tripwire warning that lists "safe emoji"
3. Check if there's a separate tripwires.md in the same directory that needs updating

This pattern was demonstrated in PR #8213 when adding the 🥞 (stacked PR) indicator: the agent updated both the main table and the related tripwire emoji list to maintain consistency.
```

### LOW Priority

#### 6. Graceful degradation subprocess pattern (SHOULD_BE_CODE)

**Location:** Docstring on subprocess wrapper OR brief addition to `docs/learned/architecture/subprocess-wrappers.md`
**Action:** CODE_CHANGE (prefer docstring) or UPDATE (if pattern truly spans multiple uses)
**Source:** [PR #8213] (dignified-python-review bot)

**Guidance:**

This is a code-level concern: when is it acceptable to use `subprocess.run` without the standard wrapper? The pattern is for optional background operations where failure should be graceful (silently ignored) rather than reported. If this guidance is added, it should be a docstring or inline comment near the wrapper functions in the subprocess utilities, not a standalone learned doc.

If evidence shows this pattern appears in multiple places, add a brief section to `docs/learned/architecture/subprocess-wrappers.md`:

```markdown
## Exception: Graceful Degradation Operations

For optional background operations where failure should be silent (e.g., best-effort notifications that shouldn't block the main workflow), using raw `subprocess.run` without wrapper is acceptable. Document the rationale inline with a comment explaining why graceful degradation is appropriate.
```

## Stale Documentation Cleanup

None identified. All referenced documentation files exist and contain expected content per existing-docs-checker analysis.

## Prevention Insights

No errors occurred during implementation. The session was notable for clean execution:

### 1. Efficient Classifier Reuse

**What happened:** Agent bypassed explicit "Use Task tool" instruction by reusing recent classifier results
**Root cause:** Phase 1 instruction doesn't account for immediate-preceding preview
**Prevention:** Document when reuse is acceptable (see item #3)
**Recommendation:** ADD_TO_DOC (medium priority)

### 2. Pre-existing Documentation Inaccuracy

**What happened:** audit-pr-docs bot caught 🚀 indicator condition inaccuracy that existed before this PR
**Root cause:** Documentation drifted from source code; nobody noticed until unrelated change triggered audit
**Prevention:** Full-document audits on any change (current system works)
**Recommendation:** CONTEXT_ONLY (system already handles this)

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Outdated review thread workflow (null line number)

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** When `is_outdated: true`, the natural instinct is to look at the line context, but the line number is null. This requires switching to whole-file analysis. Not meeting HIGH severity threshold because it's not destructive (you just won't find the issue) and doesn't fail silently (the null line number is visible). If this pattern causes repeated confusion across multiple sessions, consider promoting to tripwire.

**Criteria not met:**
- Destructive potential: 0 (doesn't break anything, just wastes time)
- Silent failure: 0 (null line number is visible in the data)
- Repeated pattern: 0 (only one occurrence observed so far)
- External tool quirk: 0 (this is expected behavior, not a quirk)

## Analysis Notes

### Session Quality

Session-bc58a084-part1 demonstrated clean execution with zero errors. Key success factors:
1. Agent loaded prerequisite `pr-operations` skill before proceeding
2. Agent correctly searched source code to understand implementation before updating docs
3. Agent updated both the table AND the related tripwire frontmatter for consistency
4. Agent used the batch thread resolution command correctly

Session-bc58a084-part2 was incomplete (user interrupted during skill loading).

### Bot Audit Effectiveness

All PR feedback came from automated bots (no human reviewers):
- **audit-pr-docs**: Caught missing 🥞 indicator AND identified pre-existing 🚀 condition inaccuracy
- **test-coverage-review**: Correctly classified terminology changes as non-significant
- **dignified-python-review**: Validated graceful degradation subprocess pattern
- **tripwires-review**: Validated TUI-specific patterns

This demonstrates the value of full-doc audits when any line changes, not just diff-line validation.

### Command Naming Resolution Path

The PR resolved a real inconsistency:
1. Documentation claimed: `erk plan submit` exists
2. Actual CLI command: `erk pr dispatch`
3. TUI before fix: Called non-existent `erk plan submit`
4. TUI after fix: Calls actual `erk pr dispatch`

The code is now correct; documentation update completes the fix.
