# Documentation Plan: Embed PlanDataTable in ObjectivePlansScreen modal

## Context

This PR (#8199) transformed the ObjectivePlansScreen modal from a static text-based plan display into a fully interactive table view. The change embeds the existing `PlanDataTable` widget—previously only used in the main `erk dash` Plans view—into a modal screen context, establishing the first instance of complex widget reuse in modal screens within the erk TUI.

The implementation revealed several cross-cutting patterns worth documenting: how to embed interactive widgets in modal screens, how to handle LBYL null safety for optional gateway fields, and how to test Textual event handlers at multiple levels (unit tests vs async pilot tests). The planning sessions also demonstrated effective git archaeology workflows for recovering work from diverged branches, and identified a prevention-worthy pattern around branch divergence detection.

Future agents working with erk's TUI system will benefit from understanding these patterns, particularly the modal embedding pattern which will likely be replicated for other modal screens that need rich interactive displays.

## Raw Materials

PR #8199

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 12    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Documentation Items

### HIGH Priority

#### 1. Null safety for optional gateway fields

**Location:** `docs/learned/architecture/null-safety-gateway-fields.md`
**Action:** CREATE
**Source:** [PR #8199]

**Draft Content:**

```markdown
---
title: Null Safety for Optional Gateway Fields
read-when:
  - accessing optional config fields from gateway context objects
  - implementing gateway methods that check self._ctx properties
  - debugging silent None-related bugs in gateway code
tripwires: 2
---

# Null Safety for Optional Gateway Fields

Gateway context objects often contain optional configuration fields that may be None.
Always use explicit `is not None` checks rather than relying on truthiness.

## The Pattern

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` for the canonical example.

The key insight is that optional config fields like `global_config` should:
1. Be extracted to a local variable first
2. Be checked with `is not None`, never implicit truthiness
3. Provide explicit defaults when None

## Why Not Truthiness?

Truthiness checks (`if config:`) fail silently when config is an empty but valid object,
or when the field has a falsy-but-meaningful value. Explicit None checks make the intent
clear and prevent subtle bugs.

## Common Mistake

Agents often write inline ternary expressions that both check and access in one line.
This creates line-length violations and readability issues. Extract the variable first.
```

---

#### 2. Branch divergence detection tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Recovering Code from Stale Branches

Before attempting to recover changes from a branch that may have diverged:

1. Run `git log --oneline master..<branch>` to count unique commits
2. Run `git diff master..<branch> --stat` to measure file divergence
3. If >10 commits or >20 files changed, investigate accumulated drift first
4. Check if related PRs already merged the desired changes

ANTI-PATTERN: Blindly attempting to reapply changes from a diverged branch
CORRECT: Understand merge history first, identify what's already in master

The planning sessions for this PR discovered a 55-file divergence that would have
caused significant confusion without this pre-flight check.
```

---

#### 3. Modal widget embedding pattern

**Location:** `docs/learned/tui/modal-widget-embedding.md`
**Action:** CREATE
**Source:** [PR #8199]

**Draft Content:**

```markdown
---
title: Modal Widget Embedding Pattern
read-when:
  - embedding interactive widgets (tables, data displays) in modal screens
  - reusing existing TUI widgets in new modal contexts
  - adding click handlers to modal screens with embedded widgets
tripwires: 4
---

# Modal Widget Embedding Pattern

This document describes how to embed rich interactive widgets (like PlanDataTable)
in modal screens, establishing the pattern first used in ObjectivePlansScreen.

## Architecture Overview

See `src/erk/tui/screens/objective_plans_screen.py` for the canonical implementation.

The pattern has four key components:
1. **Widget instantiation in compose()**: Yield the widget, initially hidden
2. **Async data loading**: Use @work decorator with call_from_thread for safe UI updates
3. **Event handling**: Use @on decorators to intercept widget messages
4. **Navigation interception**: Block parent navigation with noop bindings

## Key Decisions

- **Store row data separately**: The screen maintains `self._rows: list[RowData]` for action handlers to reference by index
- **Hide during load**: Set `table.display = False` in on_mount, show after populate
- **Query by type**: Use `self.query_one(PlanDataTable)` since some widgets don't support id= parameter

## Event Handler Pattern

Modal screens must intercept click events that would otherwise bubble to parent app.
Copy handler patterns from app.py when embedding widgets that emit custom messages.

## Vim Navigation

Add vim bindings (j/k) that delegate to table cursor actions.
Add noop bindings for left/right arrows to prevent view switching in parent.
```

---

### MEDIUM Priority

#### 4. Textual event handler testing patterns

**Location:** `docs/learned/testing/textual-event-handler-testing.md`
**Action:** CREATE
**Source:** [PR #8199]

**Draft Content:**

```markdown
---
title: Textual Event Handler Testing Patterns
read-when:
  - writing tests for Textual click handlers or keyboard actions
  - deciding between unit-style tests and async pilot tests for TUI code
  - testing modal screens with embedded widgets
tripwires: 2
---

# Textual Event Handler Testing Patterns

PR #8199 added 18 tests demonstrating two complementary approaches for testing
Textual event handlers.

## Two-Tier Testing Approach

See `tests/tui/screens/test_objective_plans_screen.py` for examples of both patterns.

### Unit-Style Tests (Fast)

For handlers that don't require app context:
1. Instantiate screen directly
2. Set internal state (`screen._rows = [...]`)
3. Create event objects manually
4. Call handlers directly and check side effects

### Async Pilot Tests (Full Integration)

For handlers requiring notify() or complex widget interaction:
1. Use `async with app.run_test() as pilot:`
2. Interact via pilot: `await pilot.press("j")`
3. Check widget state after interaction

## Guard Patterns

Handlers should guard against:
- Out-of-bounds row access (invalid index)
- Empty/None field access (missing URLs or names)
- Widget not found (query returns None)
```

---

#### 5. Pre-existing test verification pattern

**Location:** `docs/learned/testing/pre-existing-test-verification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Pre-existing Test Verification Pattern
read-when:
  - encountering test failures during implementation verification
  - distinguishing regressions from pre-existing failures
  - running verification checks before committing
tripwires: 1
---

# Pre-existing Test Verification Pattern

When tests fail during implementation verification, determine whether failures
are regressions (caused by your changes) or pre-existing issues.

## The Git Stash Pattern

```bash
git stash && pytest <failing_test> && git stash pop
```

If the test fails with changes stashed, it's pre-existing.
If it passes with changes stashed, your changes introduced the regression.

## Workflow

1. Run broad test suite
2. For each failure, verify with stash pattern
3. Document pre-existing failures
4. Exclude them from verification assertions
5. Focus debugging only on actual regressions

## Efficiency Note

Run multiple failing tests in a single stash/pop cycle rather than individual
cycles for each test. This reduces git operations and speeds verification.
```

---

#### 6. Git archaeology workflow

**Location:** `docs/learned/erk-dev/git-archaeology.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Git Archaeology Workflow
read-when:
  - recovering code from stale or diverged branches
  - investigating branch/stack confusion
  - tracing file history across rebases and merges
tripwires: 0
---

# Git Archaeology Workflow

A systematic 6-step workflow for finding code at specific points in git history.

## The Workflow

1. **Find all commits**: `git log --all --oneline -- <file>`
2. **Measure divergence**: `git diff master..<branch> --stat`
3. **List unique commits**: `git log --oneline master..<branch>`
4. **Examine specific commit**: `git show <commit> --stat` then `git show <commit>`
5. **Check file at commit**: `git show <commit>:<file>`
6. **Follow renames**: `git log --follow -- <file>`

## When to Use

This workflow is particularly valuable when:
- A branch has accumulated drift from master
- Work was lost during Graphite stack rebases
- You need to understand what changes are unique to a branch
- Related PRs may have already merged some changes

## Divergence Threshold

If step 2 shows >20 files changed or step 3 shows >10 commits,
investigate the divergence before attempting to recover changes.
```

---

#### 7. User intent clarification pattern

**Location:** `docs/learned/planning/user-intent-clarification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: User Intent Clarification Pattern
read-when:
  - user makes vague request about code changes
  - deciding between recovery vs reimplementation
  - user references "modal changes" or similar ambiguous scope
tripwires: 1
---

# User Intent Clarification Pattern

When users make ambiguous requests about code changes, clarify scope
before investing in investigation.

## The Pattern

1. List what changed (files, commits, PRs affected)
2. Ask clarifying questions about scope:
   - "Recover implementation code" vs "recover plan to reimplement"?
   - "Small fixes" vs "feature changes"?
   - "Specific file" vs "all related changes"?
3. Wait for user confirmation before deep investigation

## Common Ambiguity

"Modal changes" could mean:
- Small review feedback fixes (variable renames, error handling)
- Major feature changes (embedded widgets, new UI patterns)

## Cost of Misunderstanding

The planning sessions for this PR wasted investigation time by assuming
"modal changes" meant review feedback, when user actually wanted feature changes.
Asking "which specific changes?" immediately would have saved time.
```

---

#### 8. PlanDataTable ID limitation

**Location:** `docs/learned/tui/plan-table-widget.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: PlanDataTable Widget Limitations
read-when:
  - reusing PlanDataTable in modal screens
  - trying to assign CSS ID to PlanDataTable during construction
  - querying PlanDataTable widgets in screens
tripwires: 1
---

# PlanDataTable Widget Limitations

## ID Assignment Limitation

`PlanDataTable.__init__` does not forward `**kwargs` to `super().__init__()`,
which prevents passing `id=` during construction.

See `src/erk/tui/widgets/plan_table.py` for the widget implementation.

## Workaround

Use type-based queries instead of ID selectors:

```python
# Does NOT work:
table = self.query_one("#my-table", PlanDataTable)

# Works:
table = self.query_one(PlanDataTable)
```

## When This Matters

This limitation affects screens that embed PlanDataTable and need to reference
it in event handlers or action methods. The type-based query is actually
simpler and more Pythonic.
```

---

#### 9. Automated review bot iteration

**Location:** `docs/learned/ci/automated-review-iteration.md`
**Action:** CREATE
**Source:** [PR #8199]

**Draft Content:**

```markdown
---
title: Automated Review Bot Iteration Pattern
read-when:
  - responding to automated review feedback
  - understanding multi-round review comment patterns
  - working with github-actions bot comments
tripwires: 0
---

# Automated Review Bot Iteration Pattern

Automated review bots in erk's CI provide iterative feedback across multiple rounds.

## Feedback Pattern

1. Bot posts initial inline comment at first method with issues
2. As fixes are applied, bot posts follow-up comments with more specific requests
3. Each review round narrows scope based on remaining issues
4. Four distinct review types: dignified-python, test-coverage, code-simplifier, tripwires

## Working with Bot Feedback

- Address feedback iteratively, not all at once
- Push after each fix round to trigger re-review
- Bot comments reference specific line numbers that may shift after edits
- Check bot's inline comments, not just PR-level comments
```

---

### LOW Priority

#### 10. Plan extraction from PR bodies

**Location:** `docs/learned/planning/plan-extraction.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Plan Recovery from PR Bodies

Plans are embedded in PR descriptions inside HTML details blocks:

```html
<details>
<summary>original-plan</summary>

# Plan: [title]

[content]
</details>
```

To extract a plan from a PR:

```bash
gh pr view <number> --json body -q '.body' | python3 -c "
import sys
body = sys.stdin.read()
start = body.find('<summary>original-plan</summary>')
end = body.find('</details>', start)
if start != -1 and end != -1:
    print(body[start + len('<summary>original-plan</summary>'):end].strip())
"
```

This pattern is useful when recovering plans from merged or closed PRs
where the original plan file may no longer exist.
```

---

#### 11. Subagent exploration delegation

**Location:** `docs/learned/planning/subagent-delegation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## When to Delegate to Explore Subagent

Use Task/Explore delegation when:
- Investigation spans >3 files with complex interdependencies
- You need structured findings (widget composition, event patterns, data flow)
- Sequential file reading would miss the overall architecture

The planning sessions for PR #8199 delegated PlanDataTable architecture
investigation to Explore, receiving structured findings about:
- Column configuration
- Event message types (7 different click events)
- Data flow patterns
- Worker patterns
- Integration requirements

This structured output was more valuable than sequential file reading.
```

---

#### 12. gh CLI patterns for private repos

**Location:** `docs/learned/reference/github-cli-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Private Repository Access

For private repos, use `gh pr view` commands, not `gh api`:

```bash
# Works for private repos:
gh pr view 8156 --json body,files,reviews,comments

# Returns 404 for private repos:
gh api repos/owner/repo/pulls/8156/reviews
```

The `gh pr view` command uses gh's authentication and handles private repo access
correctly. The REST API endpoint requires different authentication handling.
```

---

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Textual widget development guide

**Location:** `docs/learned/textual/widget-development.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** Multiple screen/widget paths (NOT VERIFIED in search)
**Cleanup Instructions:** Verify all file path references in this document still exist. Update or remove references to screens/widgets that have been renamed or moved. Core content about Textual API patterns remains valid.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent null reference in gateway methods

**What happened:** Gateway methods used implicit boolean conversion (`if self._ctx.global_config:`) for optional config fields, which could fail silently if config was empty but valid.

**Root cause:** Used truthiness check instead of explicit None check.

**Prevention:** Always use `is not None` for optional field guards. Extract to local variable first: `config = self._ctx.global_config; use_val = config.use_x if config is not None else default`

**Recommendation:** TRIPWIRE - This is a cross-cutting concern affecting all gateway implementations.

### 2. Wasted investigation on diverged branches

**What happened:** Agent attempted to recover changes from a branch without first checking the scope of divergence, discovering a 55-file diff late in investigation.

**Root cause:** Jumped into recovery without measuring divergence first.

**Prevention:** Run `git log --oneline master..<branch>` and `git diff master..<branch> --stat` before attempting recovery. If >10 commits or >20 files changed, investigate accumulated drift.

**Recommendation:** TRIPWIRE - Prevents wasted effort and confusion when branches have accumulated drift.

### 3. Misunderstanding user intent from vague request

**What happened:** Agent focused on small review feedback changes when user wanted full feature implementation (embedded table widget).

**Root cause:** User said "modal changes" which agent interpreted as review feedback fixes.

**Prevention:** When user references code changes, ask clarifying questions: "recover implementation" vs "recover plan"? "small fixes" vs "feature changes"?

**Recommendation:** ADD_TO_DOC - Document in user-intent-clarification.md.

### 4. TypeError when accessing gh JSON output

**What happened:** Attempted to access JSON fields from gh CLI without parsing first.

**Root cause:** Forgot to use `json.load(sys.stdin)` before accessing fields.

**Prevention:** Use template: `gh <cmd> --json <fields> | python3 -c "import json,sys; data=json.load(sys.stdin); ..."`

**Recommendation:** CONTEXT_ONLY - Quick error caught immediately, standard Python pattern.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Null safety for optional gateway fields

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before accessing optional config fields from gateway context objects
**Warning:** Always use `is not None` for optional field guards, never rely on truthiness. Extract variable first: `config = self._ctx.global_config; use_val = config.use_x if config is not None else default`
**Target doc:** `docs/learned/architecture/tripwires.md`

This tripwire deserves high priority because silent failures in gateway code can cause subtle bugs that are difficult to diagnose. The pattern is non-obvious because Python's truthiness makes the incorrect pattern seem natural. It's cross-cutting because it applies to any gateway accessing optional context fields.

### 2. Branch divergence detection

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before attempting to recover changes from a branch
**Warning:** Run `git log --oneline master..<branch>` and `git diff master..<branch> --stat`. If >10 commits or >20 files changed, investigate accumulated drift before attempting recovery.
**Target doc:** `docs/learned/planning/tripwires.md`

The planning sessions wasted significant investigation time before discovering a 55-file divergence. This tripwire would prompt agents to check divergence scope upfront, saving time and preventing confusion.

### 3. PlanDataTable ID assignment

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When reusing PlanDataTable in modal screens
**Warning:** PlanDataTable doesn't forward kwargs to super(). Cannot pass id= during construction. Use `self.query_one(PlanDataTable)` to query by type instead.
**Target doc:** `docs/learned/tui/tripwires.md`

This is widget-specific but affects any screen embedding PlanDataTable. The workaround is simple once known, but the error message when using id= is not helpful.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. gh CLI for private repos

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Returns 404 when using `gh api` instead of `gh pr view`. Low frequency but confusing when encountered. Would warrant tripwire promotion if more agents hit this issue.

### 2. User intent clarification

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Session wasted investigation time due to ambiguous request. The pattern (ask clarifying questions) is general-purpose rather than erk-specific, so may not warrant tripwire status. Could be promoted if pattern repeats in more sessions.

### 3. Pre-existing test verification

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** The git stash pattern for distinguishing regressions from pre-existing failures can save significant debugging time. May warrant tripwire if agents repeatedly fail to distinguish regression vs pre-existing.

### 4. Plan-save interruption handling

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Low frequency but confusing when it happens. Plan exists at local path but not saved to GitHub. User may need to re-enter session or manually save. Not tripwire-worthy due to low frequency.

---

## Code Changes (SHOULD_BE_CODE items)

### 1. Line-length fix via variable extraction

**Type:** CODE_CHANGE
**Location:** dignified-python skill
**Description:** When facing line-length violations on conditional expressions, extract intermediate variables rather than using awkward line breaks. This is a coding standard, not documentation.

### 2. Branch slug generation algorithm

**Type:** CODE_CHANGE
**Location:** `erk exec plan-save` implementation docstring
**Description:** The 2-4 word, action-verb-first, max-30-char slug generation algorithm belongs in the function's docstring, not learned docs.
