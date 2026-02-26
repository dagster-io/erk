# Documentation Plan: Fix modal dismiss keys (Esc/q/Space) in TUI screens

## Context

This plan captures critical learnings from a modal key handling bug fix that revealed several cross-cutting patterns worth documenting. The implementation fixed a regression where TUI modal screens displayed "Press Esc, q, or Space to close" but those documented keys didn't actually work—instead, any *other* key dismissed the modal. The root cause was inverted conditional logic (`not in` instead of `in`) in `on_key()` handlers across three screen files.

The investigation uncovered a multi-layered lesson. First, the immediate bug pattern—using `if event.key not in (dismiss_keys):` instead of `if event.key in (dismiss_keys):`—is a subtle logic error that reads correctly until you trace its runtime behavior. Second, and more importantly, the regression was caused by a Graphite stack merge timing hazard: PR #8304 was stacked on buggy PR #8299 and squash-merged *after* PR #8309 had already fixed the bug, thereby reintroducing the buggy code. Third, the test suite failed to catch this because tests only verified that unmapped keys dismiss (which works with *both* correct and inverted logic), not that the documented dismiss keys actually work.

Future agents working on TUI modals, stacked PRs, or key handler tests would benefit from tripwires and documentation capturing these patterns. The inverted logic tripwire is high-value because the bug is non-obvious and affects all modal screens with custom `on_key()` handlers. The stack merge hazard applies to any stacked PR workflow. The testing pattern—verifying both branches of conditional logic—is a general principle that prevented this specific regression.

## Raw Materials

PR #8347

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Contradiction Resolutions

### 1. Modal Key Binding Method: BINDINGS vs on_key()

**Existing doc:** `docs/learned/tui/modal-screen-pattern.md`
**Conflict:** The existing documentation recommends using BINDINGS for modal dismiss keys ("At minimum, bind `escape` to dismiss"), but the actual codebase has 3 screens that use `on_key()` overrides with `event.prevent_default()` + `event.stop()`, which bypasses the BINDINGS system entirely. The doc doesn't mention when or why to use `on_key()` overrides.
**Resolution:** Update modal-screen-pattern.md with a new Section 8: "When to Override on_key()" explaining the tradeoffs between BINDINGS (preferred, declarative) and `on_key()` overrides (needed when consuming ALL keys to prevent leakage). Include the tripwire about inverted conditional logic.

## Documentation Items

### HIGH Priority

#### 1. Update Modal Screen Pattern with on_key() Guidance

**Location:** `docs/learned/tui/modal-screen-pattern.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8347]

**Draft Content:**

```markdown
## Section 8: When to Override on_key()

### Preferred: BINDINGS Approach

For most modal screens, use the BINDINGS approach documented above. It's declarative, inspectable, and integrates with Textual's help system.

### When on_key() Overrides Are Needed

Use `on_key()` overrides when you must consume ALL keys to prevent leakage to underlying views. This is necessary when:
- The modal overlays an interactive widget (DataTable, Input, etc.) that would otherwise capture keystrokes
- You need to prevent any key from reaching parent screens

### Pattern: Event Consumption with Conditional Dismiss

See `src/erk/tui/screens/help_screen.py` for the standard pattern. The handler must:
1. Call `event.prevent_default()` and `event.stop()` to consume the event
2. Check if the key is in the dismiss set
3. Call `self.dismiss()` only for matching keys

**CRITICAL:** When using `on_key()`, the conditional must use `if event.key in (dismiss_keys):`. Using `if event.key not in (...)` inverts the logic, causing modals to dismiss on all keys EXCEPT the documented ones.

### Reference Implementations

- HelpScreen (`src/erk/tui/screens/help_screen.py`) — Standard pattern with dismiss on escape/q/?
- PlanBodyScreen (`src/erk/tui/screens/plan_body_screen.py`) — Dismiss on escape/q/space
- LaunchScreen (`src/erk/tui/screens/launch_screen.py`) — Variant that dismisses on ANY unmapped key
```

---

#### 2. Inverted Modal Dismiss Logic Tripwire

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8347]

**Draft Content:**

```markdown
**implementing modal on_key() with "not in" conditional** → Read [TUI Modal Screen Pattern](modal-screen-pattern.md) Section 8 first. Modal dismiss logic MUST use `if event.key in (dismiss_keys):`, NOT `if event.key not in (dismiss_keys):`. The inverted logic causes modals to dismiss on all keys EXCEPT the documented dismiss keys. See `src/erk/tui/screens/help_screen.py` for correct pattern.
```

The inverted logic bug has a tripwire score of 6 (Non-obvious +2: reads correctly but behaves incorrectly; Cross-cutting +2: affects all modal screens with custom key handlers; Silent failure +2: no error, just backwards behavior). This pattern caused a regression that was fixed twice before being caught. The trigger is any time an agent implements a modal's `on_key()` handler with a membership test, and the warning should fire before the agent writes conditional logic for dismiss keys.

---

#### 3. Graphite Stack Merge Hazard Tripwire

**Location:** `docs/learned/workflows/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8347]

**Draft Content:**

```markdown
**squash-merging a PR stacked on outdated code** → If PR B is stacked on buggy PR A, and PR C fixes A, merging PR B after PR C re-introduces the bug. The squash-merge contains the old state of A. Before merging stacked PRs, rebase onto latest master and verify no conflicts with recent fixes. Use `gt stack sync` to propagate fixes downstack before merging upstack.
```

This tripwire has a score of 6 (Non-obvious +2: merge timing hazards are counterintuitive; Cross-cutting +2: applies to all stacked PR workflows; Destructive potential +2: silently reintroduces fixed bugs). The concrete example: PR #8304 was stacked on #8299 (buggy), authored before #8309 (fix), but merged after the fix, thereby reintroducing inverted logic across three files. The trigger is any time an agent is about to merge a stacked PR, and the warning should prompt verification that the stack base is up to date.

---

### MEDIUM Priority

#### 4. Modal Key Handler Testing Pattern

**Location:** `docs/learned/testing/tui-modal-testing.md`
**Action:** CREATE
**Source:** [Impl], [PR #8347]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for TUI modal screens
  - testing key handlers with allowlists or denylists
  - debugging modal dismiss behavior
category: testing
---

# TUI Modal Testing Patterns

## The Bidirectional Test Requirement

When testing modal dismiss key handlers, you MUST test BOTH directions:

1. **Positive case:** Documented dismiss keys (Esc/q/Space) actually dismiss the modal
2. **Negative case:** Unmapped/arbitrary keys do NOT dismiss (are consumed silently)

### Why This Matters

Testing only one direction misses inverted logic bugs. Example:
- Buggy code: `if event.key not in (dismiss_keys): self.dismiss()`
- Correct code: `if event.key in (dismiss_keys): self.dismiss()`

With the bug, pressing "j" (unmapped) DOES dismiss—so a test verifying "unmapped keys dismiss" passes. But Escape/q/Space do NOT dismiss—the actual bug—which goes untested.

### Pattern: pytest-asyncio with Textual Pilot

See `tests/tui/app/test_core.py` for the positive/negative test pair pattern:
- `test_help_screen_does_not_dismiss_on_unmapped_key` — Negative case
- `test_help_screen_dismisses_on_escape` — Positive case
- `test_help_screen_dismisses_on_q` — Positive case

For PlanBodyScreen examples, see `tests/tui/app/test_plan_body_screen.py`.

### Verification

After pressing a key in the test:
- Check `app.screen_stack` length to verify modal presence
- Check `isinstance(app.screen, ExpectedScreenClass)` to verify current screen
```

---

#### 5. Test Gap Tripwire for Conditional Logic

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8347]

**Draft Content:**

```markdown
**writing tests for key handlers with allowlists/denylists** → Test BOTH branches of conditional logic. Testing only alternate behavior (unmapped keys dismiss) misses primary behavior bugs (documented keys don't dismiss). An inverted condition (`not in` vs `in`) passes tests that only verify one branch. See `docs/learned/testing/tui-modal-testing.md` for the bidirectional test pattern.
```

This tripwire has a score of 4 (Non-obvious +2: tests passing creates false confidence; Repeated pattern +1: applies beyond TUI modals to any conditional logic; Cross-cutting +1: general testing principle). The trigger is any time an agent writes tests for conditional handlers, and the warning prompts coverage of both branches.

---

#### 6. Documentation-First Investigation Workflow

**Location:** `docs/learned/guide.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Bug Investigation Workflow

When investigating bugs, especially regressions, follow this efficient workflow demonstrated in TUI modal fix sessions:

### Step 1: Documentation-First Exploration

Launch parallel Explore agents to scan `docs/learned/` for existing patterns:
- Scan category-specific docs (e.g., `docs/learned/tui/` for TUI bugs)
- Scan related tripwires for known pitfalls
- Extract context before diving into source code

### Step 2: Source Code Verification

After understanding documented patterns, read actual source files to confirm current state. Compare against documented patterns to identify deviations.

### Step 3: Git History Analysis

Use git commands to trace file history and identify regression commits:
- `git log --oneline --follow <file>` — Trace file history
- `git show <commit>` — Examine specific commit diffs
- Build chronological timeline of relevant changes

### Step 4: Timeline Reconstruction

Reconstruct the sequence of commits to identify:
- When the bug was introduced
- When it was fixed (if applicable)
- When and how it regressed

This workflow is highly efficient because:
- Parallel exploration reduces latency
- Documentation provides context before code diving
- Git history reveals the full story without trial-and-error
```

---

### LOW Priority

#### 7. Git Investigation Technique

**Location:** `docs/learned/workflows/git-investigation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - tracing regression commits
  - investigating when a bug was introduced
  - analyzing file history for a bug fix
category: workflows
---

# Git Investigation Technique

## Tracing File History

Use these commands to trace how a file changed over time:

```bash
# Show commit history for a file, following renames
git log --oneline --follow <file>

# Examine a specific commit's diff
git show <commit-hash>

# Show file state at a specific commit
git show <commit-hash>:<file-path>
```

## Timeline Reconstruction Example

From PR #8347, investigating a regression:

1. `0d105f359` (#8299) — Introduced `on_key()` with buggy `not in` logic
2. `e7e8f8470` (#8309) — Fixed: changed `not in` to `in`
3. `5eabe3946` (#8304) — REGRESSION: PR stacked on #8299, merged after fix, reintroduced bug

## Pattern: Identifying Regression Commits

When a bug reappears after being fixed:
1. Find the fix commit with `git log --grep="fix modal"` or similar
2. Find when the bug reappeared with `git log --oneline --follow <file>`
3. Use `git show` to compare the regression commit against the fix commit
4. Check if the regression was a rebase/merge timing issue
```

---

#### 8. Textual Event Handling Quirk

**Location:** `docs/learned/textual/quirks.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8347]

**Draft Content:**

```markdown
## event.prevent_default() + event.stop() Blocks BINDINGS

When an `on_key()` handler calls both `event.prevent_default()` and `event.stop()`, Textual's binding system never sees the event. This means:

- BINDINGS defined on the screen will NOT fire for that key
- You must implement dismiss logic explicitly in the `on_key()` handler

This is intentional when you want to consume ALL keys to prevent leakage, but it means dismiss logic must be duplicated from BINDINGS into the handler. See `docs/learned/tui/modal-screen-pattern.md` Section 8 for the complete pattern.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Graphite Stack Reintroduces Fixed Bugs

**What happened:** PR #8304 was stacked on buggy PR #8299 and merged after PR #8309 had fixed the bug. The squash-merge re-introduced the inverted `not in` logic across three files.

**Root cause:** When a PR is stacked on an older commit and squash-merged after a fix has landed, the squash contains the pre-fix state of the base PR. The fix is effectively reverted.

**Prevention:** Before merging stacked PRs, rebase onto latest master and verify no conflicts with recent fixes. Use `gt stack sync` to propagate fixes downstack before merging upstack.

**Recommendation:** TRIPWIRE — This is a high-severity cross-cutting concern that applies to all stacked PR workflows. Added as item #3 above.

### 2. Tests Pass Despite Inverted Logic

**What happened:** Existing tests only verified that unmapped keys dismiss the modal. With both correct (`in`) and buggy (`not in`) logic, unmapped keys do cause a dismiss—so tests passed with buggy code.

**Root cause:** Testing only one branch of conditional logic creates a false sense of security. The inverted condition happens to satisfy the single-direction test.

**Prevention:** When testing conditional logic, write tests for BOTH branches: (1) that allowed keys trigger the intended behavior, (2) that disallowed keys do NOT trigger the behavior.

**Recommendation:** TRIPWIRE — This is a general testing principle worth promoting. Added as item #5 above.

### 3. on_key() Handler Blocks BINDINGS

**What happened:** Screens using `on_key()` with `prevent_default()` + `stop()` to consume keys found that their BINDINGS didn't fire, requiring explicit dismiss logic in the handler.

**Root cause:** Textual's binding system relies on event propagation. Calling both methods prevents the binding system from seeing the event.

**Prevention:** Document that when using `on_key()` with event consumption, explicit `dismiss()` calls are required for dismiss keys. BINDINGS won't work.

**Recommendation:** ADD_TO_DOC — This is a Textual API quirk worth documenting but doesn't warrant a standalone tripwire since it's specific to the `on_key()` pattern. Added to items #1 and #8 above.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Inverted Modal Dismiss Logic

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before implementing a modal's `on_key()` handler with a membership test for dismiss keys
**Warning:** "Modal dismiss logic must use `if event.key in (dismiss_keys):`, NOT `if event.key not in (dismiss_keys):`. The inverted logic causes modals to dismiss on all keys EXCEPT the documented dismiss keys."
**Target doc:** `docs/learned/tui/tripwires.md`

This is the highest-value tripwire from this session. The bug is semantically inverted—it reads as "if the key is NOT in dismiss keys, dismiss" but the intended behavior is "if the key IS in dismiss keys, dismiss." This inversion passed code review and tests because it's easy to misread. The bug affected three screen files and caused two separate fix PRs before being fully resolved.

### 2. Graphite Stack Merge Hazard

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before squash-merging a stacked PR
**Warning:** "If PR B is stacked on buggy PR A, and PR C fixes A, merging PR B after PR C re-introduces the bug. Always rebase stacked PRs after dependency PRs merge. Use `gt stack sync` to propagate fixes downstack before merging upstack."
**Target doc:** `docs/learned/workflows/tripwires.md`

This tripwire captures a merge timing hazard that is counterintuitive. Most developers assume that merging a stacked PR is safe as long as CI passes, but the squash contains the historical state of the base PR, not the current state of master. When a fix has landed between the stack creation and the merge, the squash effectively reverts the fix.

### 3. Test Gap for Conditional Logic

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, Cross-cutting +1)
**Trigger:** Before writing tests for key handlers with allowlists/denylists
**Warning:** "When testing conditional logic, write tests for BOTH branches. Testing only alternate behavior (unmapped keys dismiss) misses primary behavior bugs (documented keys don't dismiss)."
**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire promotes a general testing principle that would have caught this specific bug. The score is lower because it's a well-known testing best practice (branch coverage), but it's worth including because the specific failure mode—inverted conditionals passing single-direction tests—is non-obvious.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. event.prevent_default() + event.stop() Blocks BINDINGS

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** This is a Textual API quirk specific to the `on_key()` pattern. It doesn't warrant a standalone tripwire since it's already covered in the modal-screen-pattern.md update (Section 8). If this pattern causes additional issues beyond modal screens, it could be promoted to a tripwire in `docs/learned/textual/tripwires.md`.

### 2. Documentation-First Investigation Workflow

**Score:** 2/10 (Cross-cutting +2)
**Notes:** This is a useful workflow pattern but not a "tripwire" in the traditional sense—it's optimizing investigation efficiency rather than preventing errors. Better suited as a guide.md section (item #6) rather than a tripwire. Could be promoted if future sessions show that skipping documentation exploration leads to repeated investigation failures.
