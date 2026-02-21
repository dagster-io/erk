# Documentation Plan: Replace "issue" with "plan" in user-facing implement command output

## Context

This implementation standardized user-facing terminology in the `erk implement` command flow. The codebase previously used "issue" in output messages even when the plan backend was a draft PR rather than a GitHub issue. The fix replaced all user-visible occurrences of "issue" with the backend-agnostic term "plan" across three source files (implement.py, implement_shared.py, create_cmd.py) and their corresponding test assertions.

Documentation matters here because the change establishes a pattern: user-facing output should use domain-agnostic terminology ("plan") while internal code can retain concrete types (issue_number, draft_pr_id). Future agents implementing similar terminology updates need guidance on where to apply changes (user-facing strings) versus where to preserve existing names (internal variables). The PR also demonstrated good scope discipline by changing only strings, not refactoring internal identifiers.

Key non-obvious insight: automated code reviewers (bots) analyzing diffs may flag issues that were already fixed in the same commit. Session d0a63aa9 correctly identified this as a false positive by reading the actual test code and confirming assertions already used "plan." This pattern of false-positive detection deserves documentation so agents don't make unnecessary code changes in response to bot comments.

## Raw Materials

https://gist.github.com/schrockn/28b880a17c9867a23d92b21b1b1eb5f6

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. User-Facing Terminology Guidelines

**Location:** `docs/learned/cli/output-styling.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Terminology Conventions for User Output

When displaying identifiers in CLI output, use domain-appropriate terminology:

| Entity Type       | User-Facing Term | Variable Name    | Context                              |
| ----------------- | ---------------- | ---------------- | ------------------------------------ |
| Plan (any backend)| `plan #123`      | `issue_number`   | GitHub issue or draft PR plan        |
| Objective         | `objective #456` | `objective_id`   | Multi-plan objective tracker         |
| Pull Request      | `PR #789`        | `pr_number`      | Submitted/merged PR                  |

**Key principle:** User-facing output uses abstract terms ("plan") while internal code uses concrete types (`issue_number`, `draft_pr_id`). This decouples UX from implementation.

**Examples:**
- `"Fetching plan from GitHub..."` (not "issue")
- `"Plan #123 not found"` (not "Issue #123")
- `"Created .impl/ folder from plan #456"` (not "issue #456")

See `src/erk/cli/commands/implement.py` for reference implementation.
```

---

#### 2. Output String Migration Checklist

**Location:** `docs/learned/refactoring/systematic-terminology-renames.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
### Output String Checklist for Phase 1

When renaming display terminology, check ALL of these locations:

- [ ] CLI command docstrings (`@click.command` function docstrings)
- [ ] Help text (`help=` parameter in `@click.option`/`@click.argument`)
- [ ] Console info messages (`user_output()`, `click.echo()`)
- [ ] Error messages (both primary message and remediation context)
- [ ] Progress messages ("Fetching...", "Creating...", etc.)
- [ ] Dry-run descriptions (`f"Would {action}..."`)
- [ ] Table column headers and row content
- [ ] **Test assertions** (grep `tests/` for the old string)
- [ ] Comments in code (optional but recommended for consistency)

**Critical:** Test assertions are NOT caught by linters or type checkers. After updating production strings, always run:

```bash
grep -r '"old_term"' tests/
```
```

---

### MEDIUM Priority

#### 3. Variable Naming for Issue Types

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
### Variable Naming by Issue Type

When code handles multiple GitHub issue types, use specific variable names:

| Concept                  | Variable Name     | Type                       |
| ------------------------ | ----------------- | -------------------------- |
| Plan issue number        | `plan_id`         | `int`                      |
| Objective issue number   | `objective_id`    | `int`                      |
| Generic issue number     | `issue_number`    | `int`                      |
| Draft PR plan number     | `plan_id`         | `int` (same as issue plan) |

**Note:** When a function accepts any plan source (issue or draft PR), the parameter can remain `issue_number` internally. The distinction is primarily for clarity when multiple issue types are handled in the same scope.
```

---

#### 4. False Positive Bot Review Detection

**Location:** `docs/learned/review/bot-review-patterns.md`
**Action:** CREATE
**Source:** [PR #7721]

**Draft Content:**

```markdown
---
title: Bot Review False Positive Patterns
read_when:
  - "reviewing PR feedback from automated bots"
  - "addressing code review comments from CI bots"
---

# Bot Review False Positive Patterns

Automated code reviewers analyze diffs and may produce false positives when:

1. **Context spans commits**: Bot sees the "before" state in diff context but "after" state was already fixed in the same commit
2. **Partial file analysis**: Bot flags one location but misses related changes elsewhere in the same file
3. **Stale cached analysis**: Bot re-runs on push but uses cached metadata from previous state

## Detection Pattern

When a bot flags an issue:

1. **Read the flagged code**: Use the actual current source, not the diff
2. **Verify the pattern exists**: Check if the problematic pattern the bot describes is actually present
3. **Check related changes**: Look for fixes applied elsewhere in the PR

## Resolution

For confirmed false positives:
- Reply with specific line numbers showing the issue is already resolved
- Reference the actual code state, not the diff context
- Resolve the thread without code changes

See `src/erk/cli/commands/implement.py` and session d0a63aa9 for an example where a test assertion bot flagged lines that already used "plan" instead of "issue".
```

---

#### 5. Bot Re-Analysis Lifecycle

**Location:** `docs/learned/review/bot-review-patterns.md`
**Action:** UPDATE (append section)
**Source:** [PR #7721]

**Draft Content:**

```markdown
## Bot Re-Analysis Lifecycle

Automated reviewers follow a predictable lifecycle:

1. **Initial review**: Bot posts comments on PR creation/update
2. **Commit push**: New commits trigger re-analysis
3. **Status update**: Bot updates thread status (resolved/outdated) based on new state
4. **Resolution**: Human or bot marks threads resolved

**Key insight:** After addressing bot feedback with a new commit, the bot will automatically re-analyze. Wait for re-analysis before manually resolving threads—the bot may resolve them automatically.

Bots that demonstrated this pattern in PR #7721:
- dignified-code-simplifier: Re-analyzed after fix commits, confirmed resolution
- test-coverage-bot: Re-analyzed and auto-updated status
```

---

#### 6. Mixed PR Thread Batch Resolution

**Location:** `docs/learned/pr-operations/`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
### Batch Resolution with Mixed Thread Types

When resolving multiple PR threads in a single call, threads can have different resolution types:

**Example JSON for `erk exec resolve-review-threads`:**

```json
[
  {
    "thread_id": "PR_RT_abc",
    "reply": "Fixed: updated 'issue' to 'plan' in the reason parameter on line 124"
  },
  {
    "thread_id": "PR_RT_def",
    "reply": "Fixed: updated 'issue' to 'plan' in the reason parameter on line 124 (duplicate thread)"
  },
  {
    "thread_id": "PR_RT_ghi",
    "reply": "False positive: Tests already use 'plan' terminology. See lines 410, 492, 1008 in test_create_cmd.py"
  }
]
```

This pattern resolves both actual fixes and false-positive dismissals in a single API call.
```

---

### LOW Priority

#### 7. Verify Production Code Before Test Updates (Tripwire)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

(This is a tripwire entry, documented in the Tripwire Candidates section below)

---

## Contradiction Resolutions

None found. The terminology change from "issue" to "plan" aligns with existing documentation in `docs/learned/planning/` and `AGENTS.md`, which already use "plan" as the primary term.

## Stale Documentation Cleanup

None required. All code references in existing documentation remain valid. The internal function name `_implement_from_issue()` and variable `issue_number` were deliberately preserved, so no documentation references are phantom.

## Prevention Insights

### 1. Test Assertions Not Updated with Production Strings

**What happened:** After changing output strings from "issue" to "plan" in production code (commit b90ef115e), test assertions in `test_create_cmd.py` were not updated, causing 3 test failures.

**Root cause:** Test files were not searched when making the production string changes. The original implementation commit didn't include test updates.

**Prevention:** After any display-string changes, immediately grep test files for the old string: `grep -r '"old_term"' tests/`

**Recommendation:** ADD_TO_DOC (already captured in Output String Migration Checklist above)

### 2. Bot Comment False Positive Response

**What happened:** Session correctly identified that a test assertion bot flagged already-correct code. Could have wasted time "fixing" non-issues.

**Root cause:** Bot analyzed diff context that showed old state, but the new state in the same commit already had the fix.

**Prevention:** Always read the actual flagged code before making changes in response to bot comments.

**Recommendation:** ADD_TO_DOC (captured in Bot Review False Positive Patterns doc above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Terminology Consistency Beyond Strings

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before replacing domain terminology in user-facing strings

**Warning:** Update ALL occurrences including parameter names in error messages, help text, docstrings, and test assertions—not just display strings. Grep for the old term in `tests/` to find assertions that need updates.

**Target doc:** `docs/learned/refactoring/tripwires.md`

This tripwire is essential because the dignified-code-simplifier bot caught an inconsistent `reason` parameter that still said "issue" after display strings were changed to "plan." The error is silent—output appears correct but error contexts show stale terminology. Without this tripwire, future terminology renames will likely miss the same class of occurrences.

The cross-cutting nature (affects any command with display strings) and silent failure mode (no exception, just confusing UX) make this a strong tripwire candidate.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Verify Production Code Before Test Updates

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)

**Notes:** Session 4e0dbc59 demonstrated the correct pattern: grep production code to verify exact output string before updating test assertions. This prevents test/production mismatches. However, the failure mode (mismatched tests) is caught immediately by CI, not silently. If this pattern is violated repeatedly across multiple plans, consider promotion.

### 2. Bot Review False Positive Detection

**Score:** 2/10 (criteria: External tool quirk +1, Repeated pattern +1)

**Notes:** Specific to bot review workflow. Important for avoiding unnecessary code changes, but missing it only adds noise to PRs—it doesn't cause broken code or silent failures. The cost of missing this pattern is wasted time, not production bugs. Documentation is more appropriate than a tripwire.
