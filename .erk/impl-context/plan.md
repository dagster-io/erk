# Documentation Plan: Fix plan-save to include branch_name in skipped_duplicate response

## Context

This PR (#7944) fixes a bug where the `erk exec plan-save` command returned an incomplete JSON response when detecting a duplicate plan save attempt. The missing `branch_name` field caused Claude to fabricate branch names, leading users to attempt checking out non-existent branches. The solution introduces branch name tracking via session markers and enriches the duplicate response to match the success response schema.

Importantly, this is a **bug fix that brings implementation into alignment with already-documented contracts**. The ExistingDocsChecker confirmed that `.claude/commands/erk/plan-save.md` already stated branch_name should be in the output, `docs/learned/planning/session-deduplication.md` already describes deduplication behavior, and `docs/learned/planning/branch-name-inference.md` already explains when branch_name is available. The core patterns are already documented; documentation needs are modest and focus on tripwires, examples, and catalog updates.

The implementation session also revealed several cross-cutting insights: PR review comments showed agents repeatedly violating the "three similar lines > premature abstraction" principle; Graphite + git integration has sharp edges when mixing raw git commands with Graphite tracking; and Python silently allows duplicate function definitions. These insights warrant tripwire additions to prevent future issues.

## Raw Materials

No gist URL provided for this learn plan.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Git rebase breaks Graphite tracking

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session analysis parts 2 and 3

**Draft Content:**

```markdown
**after running `git rebase origin/$BRANCH`** → Must run `gt track --no-interactive` before `gt restack` or `gt submit`. Raw git operations change commit SHAs outside Graphite's awareness. Without retracking, Graphite's cache points to stale SHAs, causing "cannot perform on diverged branch" errors during submission.
```

---

#### 2. Duplicate function definitions in Python

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #7944] Comment at admin.py:17

**Draft Content:**

```markdown
**when extracting constants from duplicate definitions** [pattern: `def\s+(\w+)\(.*\n(?:.*\n)*def\s+\1\(`] → Read this tripwire first. Python allows duplicate function definitions and silently uses only the last one. No exception at import time, no warning during execution. Verify ALL duplicate sites are removed when consolidating functions. This was discovered in PR #7944 where three identical `claude_ci()` function definitions existed in admin.py.
```

---

#### 3. Click docstring literal block limitation

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [PR #7944] Comment at admin.py

**Draft Content:**

```markdown
**when adding constants used in Click command help text with `\b` literal blocks** → Cannot reference Python constants inside `\b` blocks. Must inline the value in the docstring. Extract the constant for runtime use only, not for help text substitution. Click's `\b` creates literal blocks where normal Python string formatting does not apply.
```

---

#### 4. Session marker expansion pattern

**Location:** `docs/learned/planning/workflow-markers.md`
**Action:** UPDATE (add new marker to catalog and pattern guidance)
**Source:** [Impl] Code diff analysis, Session analysis part 1

**Draft Content:**

Add to the "Plan Issue Tracking" section:

```markdown
### Branch Name Tracking

When saving a plan to a branch, markers track the branch name for deduplication:

```bash
# Created by plan_save.py during _save_as_draft_pr()
erk exec marker create --name plan-saved-branch --value "plnd/feature-02-22-1234"

# Read during deduplication to enrich skipped_duplicate response
BRANCH=$(erk exec marker read --name plan-saved-branch)
```

This enables the skipped_duplicate response to include the original branch name, preventing agents from fabricating branch names.

## Marker Expansion Pattern

When adding new session markers:

1. Create paired functions: `create_X_marker()` + `get_existing_X()`
2. Use `.marker` file extension for consistency
3. Store simple string or numeric values (no complex JSON)
4. Return `None` from getter when marker doesn't exist or is empty
5. Write marker during the operation (e.g., plan save success path)
6. Read marker during deduplication/retry paths
7. Consider whether the marker data should be included in JSON responses for downstream tool consumption
```

---

#### 5. Deduplication response enrichment pattern

**Location:** `docs/learned/planning/session-deduplication.md`
**Action:** UPDATE (add response schema requirements)
**Source:** [Impl] Code diff analysis, Session analysis part 1

**Draft Content:**

Add after the "Command-Level Deduplication" section:

```markdown
## Deduplication Response Schema

**Critical**: The `skipped_duplicate` response must include the same fields as the success response. Downstream consumers (slash commands, agents) expect consistent JSON structure regardless of which path was taken.

**Minimum required fields for skipped_duplicate:**

- `success`: true
- `plan_number`: The existing plan's issue/PR number
- `branch_name`: The branch where the plan was saved (retrieved from markers)
- `plan_backend`: "draft_pr" or "issue"
- `skipped_duplicate`: true
- `message`: User-friendly explanation

Without `branch_name`, agents may fabricate branch names, causing users to attempt checkout of non-existent branches.

See `src/erk/cli/commands/exec/scripts/plan_save.py` function `_save_plan_via_draft_pr()` for the implementation pattern.
```

---

### MEDIUM Priority

#### 6. PR review address workflow example

**Location:** `docs/learned/pr-operations/pr-address-workflow-example.md`
**Action:** CREATE
**Source:** [Impl] Session analysis part 4

**Draft Content:**

```markdown
---
title: PR Address Workflow Example
read_when:
  - "executing /erk:pr-address command"
  - "addressing PR review comments"
  - "learning the PR feedback loop workflow"
---

# PR Address Workflow Example

This document captures a textbook execution of the `/erk:pr-address` workflow from PR #7944.

## Workflow Steps

1. **Classification**: Haiku classifier identified actionable threads
2. **Execution Plan Display**: Showed batch with files to modify
3. **Auto-Proceed**: No user confirmation for simple batches
4. **Fix Application**: Read file, identified issue, applied fix
5. **CI Verification**: Ran `make fast-ci` via devrun agent
6. **Commit**: Single commit with clear message
7. **Thread Resolution**: Batch resolved via JSON stdin pipe to `erk exec resolve-review-threads`
8. **Verification**: Re-ran classifier to confirm no remaining threads
9. **Submit**: Force submitted to override remote divergence (local commits authoritative after PR address)
10. **PR Update**: Regenerated PR title/body from full diff

## Key Success Factors

- Use Task tool (NOT skill invocation) for classifier to ensure isolation
- Use `--no-interactive` on all `gt` commands
- Batch thread resolution via stdin pipe
- Force submit when local commits are authoritative
- Complete verification loop before moving on

## Thread Resolution Format

See `erk exec resolve-review-threads --help` for the JSON format.
```

---

#### 7. Three similar lines principle clarification

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE (add concrete examples)
**Source:** [PR #7944] Comments at app.py:877, plan_detail_screen.py:701

**Draft Content:**

Add to existing conventions section:

```markdown
## When NOT to Abstract: Three Similar Lines Principle

The principle "three similar lines > premature abstraction" exists in AGENTS.md but agents repeatedly violate it. Here are concrete examples of when NOT to abstract:

### Example 1: Different Guard Conditions

```python
# DO NOT abstract these - each has different guard conditions
if isinstance(event, CopyToClipboard):
    self.copy_to_clipboard(pyperclip.copy, event.text)

if isinstance(event, CopyPlanToClipboard):
    self.copy_plan_to_clipboard(pyperclip.copy, event.text)
```

Even though both call clipboard operations, the guard conditions (`CopyToClipboard` vs `CopyPlanToClipboard`) make them semantically distinct handlers.

### Example 2: Different Format Strings

```python
# DO NOT abstract these - each has different formatting requirements
formatted_status = f"[dim]{status}[/dim]"
formatted_title = f"[bold]{title}[/bold]"
```

The formatting differs per field. Abstracting to `format_field(style, value)` adds indirection without value.

### Rule of Thumb

Only abstract when:
- There are 4+ similar blocks (not just 2-3)
- The blocks are truly identical except for one parameterizable value
- The abstraction reduces total code volume
```

---

#### 8. Conditional dict field construction pattern

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE (add dict construction guidance)
**Source:** [PR #7944] Comment at plan_save.py:338

**Draft Content:**

Add to conventions:

```markdown
## Conditional Dict Field Construction

When building dicts with optional fields, construct completely before type annotation:

```python
# CORRECT: Build dict completely, then type
result = {
    "success": True,
    "plan_number": plan_number,
    "message": message,
}
if branch_name is not None:
    result["branch_name"] = branch_name
if plan_backend is not None:
    result["plan_backend"] = plan_backend

# The dict is now complete; consumers receive all populated fields
```

Do NOT prematurely type the dict or use TypedDict with optional fields that require runtime presence checks. The dignified-python pattern: build incrementally, consume the complete result.
```

---

#### 9. Force submit after PR address

**Location:** `docs/learned/erk/pr-address-force-submit.md`
**Action:** CREATE (or add to existing pr-address doc)
**Source:** [Impl] Session analysis part 4

**Draft Content:**

```markdown
---
title: Force Submit After PR Address
read_when:
  - "gt submit fails with 'branch updated remotely' after addressing PR comments"
  - "deciding between force submit and sync"
---

# Force Submit After PR Address

## When to Use `gt submit --force`

After addressing PR review comments, the local branch is authoritative. Use `gt submit --force --no-interactive` when:

1. You just committed fixes for review feedback
2. `gt submit` fails with "Branch has been updated remotely"
3. The remote updates were from the previous PR submission (not external changes)

## Why Force is Safe Here

The "remote updates" are typically:
- Previous WIP commits from your own PR address cycle
- Commits that are being replaced by your new, cleaner commit

Since you're the author and these are your own changes, force pushing is safe and expected.

## When NOT to Force

Do not force push if:
- Someone else has pushed to your branch
- The remote has commits you haven't reviewed
- You're unsure what the remote changes contain

In those cases, use `/erk:sync-divergence` to properly merge changes.
```

---

### LOW Priority

#### 10. Session marker catalog update

**Location:** `docs/learned/planning/workflow-markers.md`
**Action:** UPDATE (add to catalog)
**Source:** [Impl] Code diff analysis

**Draft Content:**

Update the marker table (if one exists) or add:

```markdown
| Marker Name | Created By | Purpose |
|-------------|------------|---------|
| plan-saved | plan-save-to-issue | Boolean flag that plan was saved |
| plan-saved-issue | plan-save-to-issue | Issue number of saved plan |
| plan-saved-branch | plan_save.py | Branch name where plan was saved |
| objective-context | /erk:objective-plan | Objective issue for plan linking |
| roadmap-step | /erk:objective-plan | Roadmap node for plan linking |
```

---

#### 11. Code change: Thread resolution JSON format belongs in command help

**Location:** `src/erk/cli/commands/exec/scripts/resolve_review_threads.py`
**Action:** CODE_CHANGE (add to --help text)
**Source:** [Impl] Gap analysis

The JSON format for `erk exec resolve-review-threads` is currently undocumented. Add to the command's help text:

```python
# In the command docstring or help text:
"""
Input format (via stdin):
[
  {"thread_id": "PRRT_kwDOABC...", "comment": "Fixed by extracting constant"},
  {"thread_id": "PRRT_kwDOXYZ...", "comment": "False positive - different guard conditions"}
]
"""
```

This belongs in code (command help), not learned docs.

## Contradiction Resolutions

No contradictions found. The ExistingDocsChecker confirmed that all existing documentation accurately describes the system. This PR is a bug fix that brings implementation into alignment with already-documented contracts:

- `.claude/commands/erk/plan-save.md` already states branch_name should be in the output
- `docs/learned/planning/session-deduplication.md` correctly describes deduplication behavior
- `docs/learned/planning/branch-name-inference.md` correctly explains when branch_name is available

## Stale Documentation Cleanup

No stale documentation detected. All documentation files reference existing code artifacts:

- session-deduplication.md references `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` (EXISTS)
- branch-name-inference.md references `packages/erk-shared/src/erk_shared/naming.py` (EXISTS)
- plan-save-branch-restoration.md references `src/erk/cli/commands/exec/scripts/plan_save.py` (EXISTS)

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Git push non-fast-forward after rebase

**What happened:** Git push failed with "non-fast-forward" rejection after running `git pull --rebase`
**Root cause:** Branch state diverged between local and remote after rebase operations changed commit history
**Prevention:** Before pushing, verify branch is synced; use `pull --rebase` if behind, then retry
**Recommendation:** CONTEXT_ONLY (covered by existing sync-divergence skill)

### 2. Graphite diverged branch after git operations

**What happened:** `gt submit` failed with "Cannot perform this operation on diverged branch"
**Root cause:** Running `git pull --rebase` changed commit SHAs outside of Graphite's awareness, breaking its tracking cache
**Prevention:** After ANY raw git command that modifies history (rebase, pull --rebase, cherry-pick), run `gt track --no-interactive` before `gt restack` or `gt submit`
**Recommendation:** TRIPWIRE (HIGH - silent failure, requires specific recovery sequence)

### 3. Missing fields in deduplication response

**What happened:** Claude fabricated branch names because skipped_duplicate response lacked branch_name field
**Root cause:** Deduplication path only returned minimal fields without matching success path schema
**Prevention:** When implementing deduplication, audit response schema against success path; ensure all required fields present
**Recommendation:** ADD_TO_DOC (reinforce pattern in session-deduplication.md)

### 4. Bot suggestions violate erk principles

**What happened:** Bot suggested extracting 2-3 line copy handlers into shared function
**Root cause:** Bot follows generic DRY principle without understanding erk's "three similar lines > premature abstraction" rule
**Prevention:** Always evaluate bot suggestions against erk coding standards before implementing
**Recommendation:** ADD_TO_DOC (add concrete examples to conventions.md)

### 5. Duplicate function definitions in Python

**What happened:** Three identical `claude_ci()` functions existed in admin.py, only the last was used
**Root cause:** Python allows duplicate function definitions without warning; earlier definitions are silently shadowed
**Prevention:** When extracting constants or refactoring, verify ALL duplicate sites are removed; use grep to find all definitions
**Recommendation:** TRIPWIRE (HIGH - silent runtime misbehavior, easy to miss in review)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git rebase breaks Graphite tracking

**Score:** 6/10 (Non-obvious +2, Destructive potential +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** After running `git rebase origin/$BRANCH` or `git pull --rebase`
**Warning:** Must run `gt track --no-interactive` before `gt restack` or `gt submit`. Raw git operations change commit SHAs outside Graphite's awareness.
**Target doc:** `docs/learned/erk/tripwires.md`

This is tripwire-worthy because it causes silent divergence that blocks PR submission. The recovery sequence (gt track -> gt restack -> gt submit) is non-obvious. Three different Graphite-related errors occurred across the session parts, all stemming from git/Graphite interaction.

### 2. Duplicate function definitions in Python

**Score:** 6/10 (Silent failure +2, Destructive potential +2, Non-obvious +2)
**Trigger:** When extracting constants or refactoring functions
**Warning:** Verify ALL duplicate sites are removed. Python allows duplicate function definitions and silently uses only the last one.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because Python provides no warning at import time or runtime. The wrong function silently executes. This was discovered during PR review when bot detected duplicate functions in admin.py.

### 3. Click docstring literal block limitation

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** When adding constants to Click command help text with `\b` literal blocks
**Warning:** Cannot reference Python constants inside `\b` blocks. Must inline the value in the docstring. Extract constant for runtime use only.
**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because it affects all CLI commands using `\b` in help text. The limitation is a Click framework quirk, not a Python language issue. Agents will naturally try to DRY up constants but hit this invisible wall.

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Graphite divergence after rebase recovery workflow

**Score:** 3/10 (External tool quirk +1, Repeated pattern +1, Non-obvious +1)
**Notes:** This is already covered by the higher-scoring "Git rebase breaks Graphite tracking" tripwire. The recovery workflow (gt sync vs git pull --rebase followed by gt track) could be expanded in the main tripwire's target doc.

### 2. Ruff import sorting after constant extraction

**Score:** 2/10 (Cross-cutting +1, Tooling +1)
**Notes:** Standard tooling usage that CI catches. Not worthy of tripwire status because `make fast-ci` already validates this. The pattern "run ruff check --fix after editing" is general Python hygiene, not erk-specific.
