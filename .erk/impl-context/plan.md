# Documentation Plan: Fix: Rocket emoji blocked by status indicators in dash

## Context

PR #8040 fixed a critical bug where the rocket emoji (indicating "ready to land") was unreachable for all published PRs in the TUI dashboard. The root cause was a fragile design pattern: the code scanned the rendered emoji list to determine whether to add the rocket, treating ALL emojis except the pancake as "blocking." When the published indicator (eye emoji) was present, it incorrectly blocked the rocket.

The fix replaced emoji-list scanning with direct condition checks on the underlying state fields (`has_conflicts`, `review_decision`). This architectural improvement demonstrates a generalizable anti-pattern that affects any status display system: checking derived display artifacts instead of source state. Additionally, the pancake (stacked PR) indicator was removed as a pragmatic UX trade-off to fit multiple indicators within column width constraints.

This documentation plan addresses two categories of work: updating three existing docs that now describe obsolete behavior, and creating two new docs that capture cross-cutting patterns discovered during implementation. The session analysis revealed valuable insights about test realism (using None values to sidestep bugs) and terminal emoji width calculation that deserve documentation.

## Raw Materials

PR #8040 session materials (session-6ad8ad02-part1.md, session-6ad8ad02-part2.md, diff-analysis.md)

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 9     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 1     |

## Stale Documentation Cleanup

Existing docs with semantically stale content requiring updates. These updates take priority over new documentation.

### 1. Blocking Indicator Classification Outdated

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** UPDATE
**Phantom References:** None (code references valid, but behavior description stale)
**Source:** [PR #8040]

**Cleanup Instructions:**
Lines 33-44 describe an "exclusion predicate" blocking logic that no longer exists. The phrase "all indicators except the pancake are considered blocking" must be replaced with the explicit blocking conditions: only conflicts and changes-requested block the rocket. The pancake emoji references must be historicized since that indicator was removed.

**Draft Content:**

```markdown
## Blocking Indicator Classification

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

The rocket emoji appears only when the PR is truly landable. The blocking conditions are checked directly:

- `has_conflicts is True` - merge conflicts prevent landing
- `review_decision == "CHANGES_REQUESTED"` - requested changes must be addressed

Status indicators (eye for published, construction for draft) are informational and do not block the rocket. They appear alongside the rocket when applicable.

See `_build_indicators()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` for implementation.

**Historical note:** The pancake emoji for stacked PRs was removed in PR #8040 to reduce column width. Stacked detection logic remains intact via `base_ref_name` and `get_parent_branch()`, but the visual indicator is no longer displayed.
```

---

### 2. Visual Status Indicators Blocking Logic Outdated

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md`
**Action:** UPDATE
**Phantom References:** None
**Source:** [PR #8040]

**Cleanup Instructions:**
Lines 63-74 describe "all indicators except pancake" blocking logic and list pancake as an informational indicator. Update the "Blocking vs. Informational Indicators" section to reflect the explicit blocking list and remove pancake from the informational list.

**Draft Content:**

```markdown
## Blocking vs. Informational Indicators

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

Indicators are classified by their relationship to the rocket (ready-to-land) signal:

**Blocking indicators** (suppress the rocket):
- Conflicts emoji - merge conflicts prevent landing
- X emoji - changes requested in review must be addressed

**Informational indicators** (appear alongside rocket):
- Eye emoji - PR is published (not draft)
- Construction emoji - PR is in draft state

The rocket emoji represents "ready to land" state. It appears when all merge-blocking conditions are resolved: checks pass, no unresolved comments, no conflicts, and no changes requested.

See `_build_indicators()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` for the implementation that checks `has_conflicts` and `review_decision` directly.
```

---

### 3. Lifecycle Stacked State Section Outdated

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Phantom References:** None
**Source:** [PR #8040]

**Cleanup Instructions:**
Lines 1080-1084 reference the pancake emoji and outdated blocking behavior. Update the "Stacked State" section to note pancake removal and correct the blocking indicator description.

**Draft Content:**

```markdown
## Stacked State

Stacked PRs (those based on another non-master branch) are detected via `base_ref_name` comparison with `get_parent_branch()`. As of PR #8040, the pancake emoji indicator for stacked PRs is no longer rendered in the TUI to reduce column width.

The stacked detection logic remains functional for internal operations but is not displayed to users. For visual indicator behavior, see `docs/learned/tui/stacked-pr-indicator.md`.

Only conflicts and changes-requested block the rocket indicator; being stacked does not affect landability.
```

---

## Documentation Items

### HIGH Priority

#### 1. Update stacked-pr-indicator.md blocking classification

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** UPDATE
**Source:** [PR #8040]

**Draft Content:**

```markdown
## Rocket Indicator Logic

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

The rocket emoji indicates a PR is ready to land. It appears only when:
1. Stage is `impl` (implementing)
2. `has_conflicts is not True`
3. `review_decision != "CHANGES_REQUESTED"`
4. `checks_passing is True`
5. `has_unresolved_comments is not True`

Status indicators (eye for published, construction for draft) are informational and appear alongside the rocket when conditions are met.

**Tripwire:** When implementing indicator logic, check source state fields directly. Do not scan the built indicator list to determine whether to add more indicators. Example: check `has_conflicts` boolean, not the presence of conflict emoji in the indicator string.
```

---

#### 2. Update visual-status-indicators.md semantic distinction

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md`
**Action:** UPDATE
**Source:** [PR #8040]

**Draft Content:**

```markdown
## Status vs Semantic Indicators

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

**Status indicators** communicate PR state without affecting actions:
- Eye emoji (published) - informs user the PR is not a draft
- Construction emoji (draft) - informs user the PR is a draft

**Semantic indicators** represent conditions that enable or block actions:
- Rocket emoji (ready to land) - all merge-blocking conditions resolved
- Conflicts emoji (has conflicts) - merge blocked until resolved
- X emoji (changes requested) - merge blocked until addressed

The distinction matters for implementation: status indicators should never affect whether semantic indicators appear. Check blocking conditions directly from state fields, not by scanning the indicator list.
```

---

#### 3. Update lifecycle.md stacked references

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [PR #8040]

See Stale Documentation Cleanup section above for draft content.

---

### MEDIUM Priority

#### 4. Create direct condition checking anti-pattern doc

**Location:** `docs/learned/architecture/direct-condition-vs-derived-output.md`
**Action:** CREATE
**Source:** [Impl] [PR #8040]

**Draft Content:**

```markdown
---
title: Direct Condition Checking vs Derived Output Scanning
read_when:
  - implementing conditional logic based on display strings or emoji
  - building status indicator systems
  - deciding whether to scan rendered output vs checking state
tripwires:
  - action: "scanning emoji list or display strings to determine program logic"
    warning: "Check source state fields directly (has_conflicts, review_decision). Display artifacts are presentation layer, not state layer."
---

# Direct Condition Checking vs Derived Output Scanning

## Pattern

When implementing conditional logic that depends on multiple states, check source state fields directly rather than scanning derived outputs (display strings, emoji, formatted text) for implicit meaning.

## Anti-Pattern: Derived Output Scanning

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py, _build_indicators -->

**Problem:** Logic that inspects display-layer artifacts to make decisions about program behavior.

**Why this fails:**
- Fragile: Adding new informational indicators breaks logic (e.g., adding eye emoji for "published" blocked the rocket)
- Implicit: "Blocking" concept exists only as negation, not explicit list
- Maintenance burden: Every new indicator requires checking if it affects other indicators

## Correct Pattern: Source State Checks

**Solution:** Check the underlying state fields that determine behavior.

The implementation in `_build_indicators()` now checks `has_conflicts` and `review_decision` directly instead of scanning the emoji list. This makes blocking conditions explicit and adding informational indicators safe.

See `_build_indicators()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`.

## Case Study: Rocket Emoji Bug (PR #8040)

**Symptom:** Published PRs with passing checks never showed rocket emoji.

**Root cause:** Original logic treated ALL emoji except pancake as blocking, including the eye (published) status indicator.

**Impact:** Rocket emoji became unreachable for any published PR, defeating its purpose as "ready-to-land" signal.

**Fix:** Check `has_conflicts` and `review_decision` directly instead of scanning emoji list.

## When to Apply This Pattern

**Use direct condition checks when:**
- Multiple states determine whether an action is allowed
- Display logic combines multiple indicators into one string
- Adding new display elements shouldn't change behavior logic

**Danger signs (derived output scanning):**
- Scanning formatted strings for specific characters/emoji
- Using "all except X" exclusion predicates
- Logic depends on display ordering or presence of visual markers

## Related Patterns

See `docs/learned/desktop-dash/visual-status-indicators.md` for blocking vs informational classification.
```

---

#### 5. Create emoji column width calculation doc

**Location:** `docs/learned/tui/emoji-column-width.md`
**Action:** CREATE
**Source:** [Impl] [PR #8040]

**Draft Content:**

```markdown
---
title: Emoji Column Width Calculation
read_when:
  - designing TUI columns that display emoji
  - calculating terminal column widths for status indicators
  - adjusting table layout to fit emoji content
tripwires:
  - action: "increasing table column widths in TUI for emoji displays"
    warning: "Calculate realistic worst-case width: (max_emoji_count * 2) + spaces_between. Consider whether dropping an indicator is more pragmatic than expanding the column."
---

# Emoji Column Width Calculation

## Pattern

Terminal emoji typically render as 2 cells wide. When calculating column width for status indicators or emoji displays, use the formula:

```
width = (emoji_count * 2) + space_count
```

## Example from PR #8040

**Scenario:** Status column needs to display up to 3 emoji with spaces between them.

**Calculation:**
- Maximum emoji: 3 (e.g., eye + conflicts + changes-requested)
- Spaces between: 2
- Width = (3 * 2) + 2 = 8 cells minimum

**Implemented width:** 7 (pragmatic choice, fits 3 emoji with tight spacing)

<!-- Source: src/erk/tui/widgets/plan_table.py, PlanDataTable._setup_columns -->

See `_setup_columns()` in `src/erk/tui/widgets/plan_table.py` for the column width configuration.

## Trade-offs

**Column width constraints:**
- Wider status column = less space for other columns (plan title, branch name)
- Sometimes dropping an indicator is more pragmatic than expanding the column

**Example from PR #8040:**
- Agent proposed width=10 to fit 4 emoji (including pancake for stacked)
- User rejected as "too wide"
- Solution: Dropped pancake indicator, reduced width to 7

**Lesson:** Prefer table compactness over comprehensive indicator display when space is constrained.

## Realistic Testing

When designing emoji columns, test with realistic multi-emoji combinations:
- Don't test only single emoji cases
- Consider worst-case scenarios (all indicators present)
- Account for spaces between emoji for readability
```

---

#### 6. Update dashboard-columns.md status column width

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [PR #8040]

**Draft Content:**

```markdown
## Status Column (sts)

<!-- Source: src/erk/tui/widgets/plan_table.py, PlanDataTable._setup_columns -->

**Width:** 7 characters (changed from 4 in PR #8040)

**Reasoning:** The column must accommodate multiple simultaneous indicators. Worst-case: 3 emoji with spaces (e.g., eye + rocket for published ready-to-land PRs).

**Width calculation:** (3 emoji * 2 cells) + 2 spaces = 8 cells, rounded to 7 for visual spacing.

See `_setup_columns()` in `src/erk/tui/widgets/plan_table.py` for column configuration.
```

---

### LOW Priority

#### 7. Update ready-to-land terminology

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** UPDATE
**Source:** [PR #8040]

**Draft Content:**

```markdown
## Terminology

The rocket emoji indicates a PR is **ready to land** (not "ready to merge"). This terminology aligns with erk's vocabulary where "landing" refers to merging a PR to the target branch.

A PR is ready to land when:
- Checks pass
- No unresolved review comments
- No merge conflicts
- No changes requested in review
```

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Display Logic Architecture: Checking Derived Artifacts vs Source State

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before implementing conditional logic based on emoji presence or display strings
**Warning:** Check source state fields (has_conflicts, review_decision) directly. Do not scan derived display artifacts like emoji strings to determine program behavior.
**Target doc:** `docs/learned/architecture/direct-condition-vs-derived-output.md` (new)

This tripwire is warranted because the bug demonstrated a silent failure mode: the rocket emoji simply never appeared for published PRs, with no error or warning. The pattern is cross-cutting because any status display system (TUI, CLI output, desktop dash) could fall into the same trap. The error was non-obvious because it required understanding that the emoji list was derived from state, not the source of truth.

The anti-pattern (emoji-scanning) looked correct at first glance: "check if any blocking indicators are present before adding the rocket." The flaw only surfaced when a new informational indicator (eye for published) was inadvertently treated as blocking. Future agents need this tripwire to avoid reintroducing similar fragile precedence systems.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Realism: None Values Sidestepping Conditionals

**Score:** 2/10 (Non-obvious +2)
**Trigger:** When writing tests for lifecycle/status display logic
**Warning:** Avoid None values that skip conditionals. Use realistic values (is_draft=False for published PRs) to exercise actual code paths.
**Target doc:** `docs/learned/testing/tripwires.md`
**Notes:** Flagged in session as LOW severity. The test with `is_draft=None` passed but didn't catch the bug because it sidestepped the code path that added the published indicator. While this is valuable to document, it doesn't rise to tripwire level because: (1) it's a general testing best practice, not erk-specific; (2) the consequence is a missed bug, not data loss or rework.

**Recommendation:** Add as a testing pattern in the LOW priority section below rather than promoting to tripwire status. The insight is valuable but the severity doesn't warrant interrupting agent workflows.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Fragile Emoji-Scanning Precedence Logic

**What happened:** Original implementation used `any(i != "pancake" for i in indicators)` to determine whether to show the rocket. This treated ALL emojis except the pancake as blocking, including informational status indicators.

**Root cause:** Design conflated display layer (emoji) with state layer (has_conflicts, review_decision). The "blocking" concept existed only implicitly as "everything except pancake."

**Prevention:** Design indicator systems to check source conditions directly. Enumerate blocking conditions explicitly (conflicts, changes-requested) rather than using exclusion predicates.

**Recommendation:** TRIPWIRE - This is a cross-cutting pattern that applies to any status display system. Scored 6/10 in tripwire analysis.

### 2. Tests Passing with Unrealistic None Values

**What happened:** The existing test `test_impl_checks_passing_no_comments_shows_rocket()` used `is_draft=None`, which avoided the branch that added the published indicator. The test passed, but real published PRs failed.

**Root cause:** Using None as a default value in tests to avoid specifying "irrelevant" parameters. But None bypassed conditionals that would have exposed the bug.

**Prevention:** Prefer concrete test values (`True`/`False`, `draft`/`published`) over None sentinels, especially for display logic. Test with realistic parameter combinations that match production scenarios.

**Recommendation:** ADD_TO_DOC - Include in testing tripwires documentation as a LOW priority pattern. Severity is low because the consequence is missing a bug, not causing data loss.

### 3. Column Width Underestimation

**What happened:** Agent initially proposed `width=4` for status column, but this only fits approximately 2 emoji. When multiple indicators needed to appear simultaneously (eye + rocket), they were truncated or misaligned.

**Root cause:** Underestimating terminal rendering width of emoji (2 cells each) and not considering worst-case multi-emoji combinations.

**Prevention:** When designing status columns with emoji, calculate: `(max_emoji_count * 2) + (spaces_between)`. Test with realistic multi-emoji combinations, not just single emoji cases.

**Recommendation:** ADD_TO_DOC - The emoji column width formula is documented in the new `emoji-column-width.md` doc as a MEDIUM priority item.

---

## Implementation Notes

### Documentation Update Order

For consistency, update docs in this order:
1. **Stale cleanup first:** Update the three existing docs with outdated blocking logic
2. **New docs second:** Create the two new pattern docs
3. **Tripwire additions last:** Add the tripwire to the architecture doc and testing tripwires

### Source Pointer Guidelines

All draft content uses the two-part source pointer format per `docs/learned/documentation/source-pointers.md`:
- HTML comment for machine-readable staleness detection
- Prose reference for agent navigation

The primary source for indicator logic is `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`, function `_build_indicators()`. The column width configuration is in `src/erk/tui/widgets/plan_table.py`, method `PlanDataTable._setup_columns()`.

### What Not to Document

The following items from the diff analysis are intentionally excluded:
- Test file changes (self-documenting via test cases)
- Column width vs indicator trade-off details (context-specific decision, not generalizable)
- Pancake indicator removal mechanics (captured in the doc updates, doesn't need its own doc)
