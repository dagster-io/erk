# Documentation Plan: Restore abbreviated stage names in TUI dashboard

## Context

PR #7852 represents a significant refinement to the TUI dashboard's lifecycle display system. The work reverted changes from PR #7790 that had inadvertently used full stage names ("implementing", "implemented") which were truncated in the 9-character stage column, and restored the abbreviated forms ("impling", "impld"). Beyond this revert, the PR introduced several enhancements: a new ready-to-merge indicator (rocket emoji), unified emoji positioning (all suffixes), extended conflict/review indicators to the implemented stage, and critical test infrastructure fixes for parallel xdist execution.

This multi-session implementation (7 sessions) revealed important patterns around TUI column width calculations, stage detection mechanics, and test isolation. The iterative nature of the work—with user feedback driving bug fixes for emoji disappearance and subsequent width adjustments—demonstrates that TUI changes require visual verification beyond unit tests. Future agents working on lifecycle display or TUI tables will benefit from understanding these lessons, particularly the subtle interaction between emoji positioning and column width truncation.

The documentation needs fall into three categories: tripwires for silent failure modes (stage detection, temp directory scanning, emoji width), new conceptual documentation (lifecycle indicators, false positive patterns), and updates to existing docs (column widths, lifecycle display).

## Raw Materials

PR #7852 session analyses and diff analysis

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 13    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 5     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Stage detection by substring matching [TRIPWIRE]

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 867c9114, [PR #7852]

**Draft Content:**

```markdown
**Before changing stage display names in compute_lifecycle_display()** --> Read [Lifecycle Indicators](lifecycle-indicators.md) first. CRITICAL: format_lifecycle_with_status() detects stages by substring matching (e.g., "impling" in lifecycle_display). Changing display strings MUST update detection logic to match new substrings. Breaking this causes emoji indicators to silently not appear on correct stages.

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, format_lifecycle_with_status -->
```

---

#### 2. Shared temp directory scanning anti-pattern [TRIPWIRE]

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 33d62ce6, ac147343, [PR #7852]

**Draft Content:**

```markdown
**Before writing tests that scan temp directories or use tempfile operations** --> Read [Temp Isolation for xdist](temp-isolation-xdist.md) first. FORBIDDEN: Tests MUST NOT scan shared system directories (tempfile.gettempdir()) for pattern-matched files under parallel xdist execution. Use monkeypatch: `monkeypatch.setattr(tempfile, 'tempdir', str(tmp_path / 'temp'))` to isolate temp operations per test. Remove manual cleanup; pytest auto-cleans tmp_path.
```

---

#### 3. TUI column width calculation for emojis [TRIPWIRE]

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 867c9114, c9098c54, [PR #7852]

**Draft Content:**

```markdown
**Before adding or repositioning emojis in TUI table columns** --> Read [Lifecycle Indicators](lifecycle-indicators.md) first. WARNING: Emojis count as 2 visual columns in terminal display. Calculate column width: max_text_length + space + (emoji_count x 2) + breathing_room. Textual silently truncates content if width is insufficient. Suffix emojis get cut off entirely when truncated. MUST verify visually with `erk dash` after changes; unit tests cannot catch truncation.
```

---

#### 4. Lifecycle indicator composition and priority

**Location:** `docs/learned/tui/lifecycle-indicators.md`
**Action:** CREATE
**Source:** [Impl] Sessions 867c9114, c9098c54, 6a0f7d3d, [PR #7852]

**Draft Content:**

```markdown
---
title: Lifecycle Indicators
read_when:
  - "modifying emoji indicators in TUI stage column"
  - "adding new status indicators to lifecycle display"
  - "understanding how draft/conflict/ready indicators work"
tripwires:
  - action: "changing stage display names in compute_lifecycle_display()"
    warning: "CRITICAL: format_lifecycle_with_status() detects stages by substring matching. Changing display strings MUST update detection logic in the same file to match new substrings."
    score: 8
  - action: "adding or repositioning emojis in TUI table columns"
    warning: "Emojis count as 2 visual columns. Calculate width accounting for emoji width and verify visually with erk dash."
    score: 6
---

# Lifecycle Indicators

The TUI dashboard stage column displays abbreviated lifecycle stages with emoji status indicators. All indicators appear as suffixes (right-aligned) after the stage name.

## Indicator Types

| Indicator | Emoji | Stages | Condition |
|-----------|-------|--------|-----------|
| Draft | rocket-construction | planned, implementing, review | PR is in draft state |
| Published | eyes | planned, implementing, review | PR published (not draft) |
| Conflict | collision | implementing, implemented, review | PR has merge conflicts |
| Approved | check-mark | review | PR approved by reviewer |
| Changes Requested | cross-mark | review | Reviewer requested changes |
| Ready to Merge | rocket | implemented | All clear: checks pass, no unresolved comments, no conflicts |

## Indicator Priority and Composition

Indicators are composed into a unified suffix. The rocket (ready-to-merge) indicator only appears when no negative indicators are present:

- If checks fail, conflicts exist, or unresolved comments exist: no rocket shown
- The rocket represents "all clear" state, so any problem suppresses it

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, format_lifecycle_with_status -->

See `format_lifecycle_with_status()` for the complete detection and composition logic.

## Stage Abbreviations

The stage column (width=11) requires abbreviated stage names to fit alongside emoji indicators:

| Full Name | Abbreviation | Characters |
|-----------|--------------|------------|
| implementing | impling | 7 |
| implemented | impld | 5 |
| planned | planned | 7 |
| review | review | 6 |

Longest case: "impling rocket-construction" = 7 + 1 + 2 = 10 columns (fits in width 11).

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display -->

## Detection Mechanism

Stage detection uses substring matching on the formatted display string. This is intentional internal consistency within the same module, not fragile coupling.

When changing abbreviations, update both:
1. Display computation in compute_lifecycle_display()
2. Detection patterns in format_lifecycle_with_status()

## Column Width Calculation

When adding emojis to fixed-width columns:
- Emojis count as 2 visual columns
- Calculate: max_text + space + (emoji_count x 2) + margin
- Verify visually with `erk dash` - unit tests cannot catch truncation

## Related Documentation

- [Dashboard Column Inventory](dashboard-columns.md) - column widths and presence conditions
- [Plan Lifecycle](../planning/lifecycle.md) - lifecycle stage values and transitions
```

---

#### 5. False positive PR review patterns

**Location:** `docs/learned/reviews/false-positive-patterns.md`
**Action:** CREATE
**Source:** [Impl] Sessions 6a0f7d3d, 8fb7cb86, [PR #7852]

**Draft Content:**

```markdown
---
title: False Positive PR Review Patterns
read_when:
  - "receiving automated reviewer comments on PRs"
  - "evaluating whether a bot comment is actionable"
  - "dismissing or addressing PR review threads"
tripwires:
  - action: "accepting automated reviewer comments on PRs"
    warning: "VERIFY: Systematically check automated reviewer comments against PR intent and git diff before accepting. Check for known false positive patterns."
    score: 4
---

# False Positive PR Review Patterns

Automated reviewers flag patterns without understanding context. This document catalogs common false positives to help agents quickly identify comments that can be dismissed.

## Identification Process

Before accepting an automated reviewer comment:

1. **Read the PR context** - title, description, linked plan
2. **Check git diff** - what lines were actually changed vs pre-existing
3. **Verify against PR intent** - is the bot complaining about the very thing the PR is trying to do?

If the flagged pattern IS the PR's purpose, it's a false positive.

## Common False Positive Patterns

### 1. Hardcoded Display Strings for UI Constraints

**Bot complaint:** "Abandoning dynamic patterns for hardcoded strings"

**Reality:** UI constraints (column width, terminal display) require static abbreviated strings. Dynamic interpolation would exceed available space.

**Example:** Using "impling" instead of f"{stage}" when stage="implementing" would truncate.

**Dismiss when:** The PR's stated purpose involves abbreviation or space-constrained UI.

### 2. Internal Module Coupling

**Bot complaint:** "Fragile substring matching" or "Brittle coupling"

**Reality:** Producer and consumer are in the same module. This is intentional internal consistency, not cross-module fragility.

**Example:** compute_lifecycle_display() and format_lifecycle_with_status() are in the same file and intentionally coordinated.

**Dismiss when:** Both the producing and consuming code are in the same file/module.

### 3. Test Helper Defaults Flagged as Production Violation

**Bot complaint:** "Default parameter values violate coding standards"

**Reality:** Test helpers may use defaults for ergonomics. The no-defaults rule applies to production code, not test infrastructure.

**Example:** A test helper with `def _format_lifecycle(checks_passing=None, ...)` is acceptable even when production requires explicit params.

**Dismiss when:** The function is clearly test infrastructure (prefixed with `_`, in test file).

### 4. Pre-Existing Issues Flagged in Current PR

**Bot complaint:** Flags violation on lines the current PR didn't change.

**Reality:** The issue existed before this PR. Current PR is not responsible for pre-existing problems unless explicitly fixing them.

**Detection:** Check `git diff master...HEAD` to see if the flagged line was actually modified.

**Dismiss when:** Git diff shows the line was not changed by this PR.

## Efficient Dismissal Workflow

For batch false positives, use the PR thread resolution command:

```bash
erk exec resolve-review-threads --stdin < threads.json
```

Include clear explanations referencing this document and prior investigations.

## Related Documentation

- [Scope Boundary Analysis](scope-boundary-analysis.md) - distinguishing in-scope vs pre-existing issues
- [pr-operations skill](.claude/skills/pr-operations.md) - PR thread resolution commands
```

---

### MEDIUM Priority

#### 6. Stage abbreviation mapping and rationale

**Location:** `docs/learned/tui/lifecycle-abbreviations.md`
**Action:** CREATE
**Source:** [Impl] Sessions ec5ab77c, 867c9114, [PR #7852]

**Draft Content:**

```markdown
---
title: Lifecycle Abbreviations
read_when:
  - "changing stage display names"
  - "understanding why 'impling' instead of 'implementing'"
  - "calculating stage column width"
---

# Lifecycle Abbreviations

The TUI stage column uses abbreviated stage names to fit within width constraints while preserving emoji indicators.

## Abbreviation Table

| Stage | Display | Characters | Rationale |
|-------|---------|------------|-----------|
| implementing | impling | 7 | "implement..." would truncate, losing meaning |
| implemented | impld | 5 | Shortest unambiguous form |
| planned | planned | 7 | Short enough to fit |
| review | review | 6 | Short enough to fit |

## History

PR #7790 inadvertently changed abbreviated names back to full names. PR #7852 reverted this because:
- Stage column width is 11 characters
- "implementing" (12 chars) gets truncated to "implement..." which loses meaning
- "impling" + emoji indicators fits cleanly

## Column Width Calculation

Stage column width = 11 characters

Longest case: "impling" (7) + space (1) + emoji (2) + margin (1) = 11

## Consistency with TUI Headers

Other TUI columns use abbreviations:
- `chks` (checks)
- `wt` (worktree)
- `st` (stage)

Abbreviated stage names follow this established pattern.

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display -->
```

---

#### 7. Temp directory test isolation for xdist

**Location:** `docs/learned/testing/temp-isolation-xdist.md`
**Action:** CREATE
**Source:** [Impl] Sessions 33d62ce6, ac147343, [PR #7852]

**Draft Content:**

```markdown
---
title: Temp Directory Isolation for xdist
read_when:
  - "writing tests that use tempfile module"
  - "debugging flaky tests under parallel execution"
  - "tests scanning directories for pattern-matched files"
tripwires:
  - action: "writing tests that scan temp directories or use tempfile operations"
    warning: "FORBIDDEN: Do not scan shared tempfile.gettempdir(). Monkeypatch tempfile.tempdir to tmp_path for xdist isolation."
    score: 7
---

# Temp Directory Isolation for xdist

Tests that scan shared system temp directories are flaky under parallel xdist execution. Other workers create matching files between snapshots, causing false positives or negatives.

## The Problem

```python
# WRONG: Scans shared temp directory
def test_cleanup(tmp_path):
    before = set(Path(tempfile.gettempdir()).glob("erk-plan-*.idx"))
    # ... do operation ...
    after = set(Path(tempfile.gettempdir()).glob("erk-plan-*.idx"))
    assert before == after  # FLAKY: other workers may have created files
```

## The Solution

```python
# CORRECT: Isolated temp directory
def test_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Create isolated temp directory
    isolated_temp = tmp_path / "temp"
    isolated_temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(isolated_temp))

    # ... do operation (tempfile calls now use isolated_temp) ...

    # Assert on isolated directory only
    remaining = list(isolated_temp.glob("erk-plan-*.idx"))
    assert remaining == [], f"Files not cleaned up: {remaining}"
    # No manual cleanup needed - pytest auto-cleans tmp_path
```

## Key Elements

1. **Add fixtures**: `tmp_path: Path, monkeypatch: pytest.MonkeyPatch`
2. **Create subdirectory**: `isolated_temp = tmp_path / "temp"`
3. **Monkeypatch before operations**: `monkeypatch.setattr(tempfile, "tempdir", str(isolated_temp))`
4. **Assert on isolated directory**: Only check files in `isolated_temp`
5. **Remove manual cleanup**: pytest handles `tmp_path` cleanup automatically

## When This Applies

- Tests using `tempfile.mkstemp()`, `tempfile.NamedTemporaryFile()`, etc.
- Tests globbing for temp file patterns
- Tests that verify file cleanup
- Any test that might run in parallel with similar tests
```

---

#### 8. Three-way boolean validation for "all clear" states

**Location:** `docs/learned/architecture/three-way-validation.md`
**Action:** CREATE
**Source:** [Impl] Session c9098c54, [PR #7852]

**Draft Content:**

```markdown
---
title: Three-Way Boolean Validation
read_when:
  - "checking multiple optional boolean conditions"
  - "implementing 'all clear' or 'all healthy' states"
  - "handling optional PR status fields"
---

# Three-Way Boolean Validation

When checking multiple optional boolean fields for an "all clear" state, use explicit identity checks to handle None gracefully.

## The Pattern

```python
# For required positive conditions:
if checks_passing is True:  # Must be explicitly True, not just truthy
    ...

# For absence of problems:
if has_conflicts is not True:  # Passes for False OR None
    ...
```

## Why Not Simple Truthiness?

Optional boolean fields have three states: True, False, None (unknown).

| Value | `bool(value)` | `value is True` | `value is not True` |
|-------|---------------|-----------------|---------------------|
| True | True | True | False |
| False | False | False | True |
| None | False | False | True |

For "all clear" states:
- **Required positives** (checks must pass): Use `is True` - None means "don't know", not "passed"
- **Absence of problems** (no conflicts): Use `is not True` - None means "don't know if conflicting", acceptable for rocket

## Real Example: Ready-to-Merge Indicator

```python
# Show rocket only when ALL conditions are healthy
if (checks_passing is True and
    has_conflicts is not True and
    has_unresolved_comments is not True):
    indicators.append("rocket")
```

This ensures:
- Checks must explicitly pass (not just "not failing")
- Conflicts and comments can be None (unknown) without blocking the indicator
- Any known problem blocks the indicator

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, format_lifecycle_with_status -->
```

---

#### 9. Scope boundary analysis for PR reviews

**Location:** `docs/learned/reviews/scope-boundary-analysis.md`
**Action:** CREATE
**Source:** [Impl] Session 8fb7cb86, [PR #7852]

**Draft Content:**

```markdown
---
title: Scope Boundary Analysis
read_when:
  - "evaluating whether a reviewer comment is in scope"
  - "deciding whether to fix a flagged issue"
  - "determining if an issue is pre-existing"
---

# Scope Boundary Analysis

When automated reviewers flag issues, determine whether the issue was introduced by the current PR or is pre-existing.

## The Process

1. **Check git diff**: `git diff master...HEAD -- path/to/file.py`
2. **Examine flagged lines**: Were they modified by this PR?
3. **Classify the issue**:
   - **In-scope**: Lines were changed by this PR - fix is appropriate
   - **Out-of-scope**: Lines pre-date this PR - fix is optional scope creep

## Decision Framework

| Line Status | Action |
|-------------|--------|
| Modified in this PR | Address the comment |
| Added in this PR | Address the comment |
| Unchanged from master | Document as pre-existing, defer unless explicitly fixing |

## Why This Matters

1. **Scope creep**: Fixing unrelated issues in a PR obscures the PR's purpose
2. **Risk**: Unrelated fixes may introduce regressions outside the PR's test scope
3. **Efficiency**: Pre-existing issues can be tracked separately for dedicated cleanup

## Example Workflow

```bash
# Check what this PR actually changed
git diff master...HEAD -- src/erk/file.py | head -50

# Bot flagged line 42 - was it changed?
git blame src/erk/file.py -L 42,42
# If commit is from master, it's pre-existing

# Decision: Document as out-of-scope, create separate issue if warranted
```

## Related Documentation

- [False Positive PR Review Patterns](false-positive-patterns.md) - common patterns to dismiss
```

---

#### 10. Lifecycle display rendering pipeline

**Location:** `docs/learned/tui/lifecycle-rendering-pipeline.md`
**Action:** CREATE
**Source:** [Impl] Sessions 867c9114, c9098c54, [PR #7852]

**Draft Content:**

```markdown
---
title: Lifecycle Rendering Pipeline
read_when:
  - "modifying how lifecycle stages are displayed"
  - "debugging why indicators don't appear"
  - "understanding the three-step lifecycle display flow"
---

# Lifecycle Rendering Pipeline

The TUI lifecycle display flows through three stages, each with specific responsibilities.

## Pipeline Overview

```
Step 1: compute_lifecycle_display()
  └── Returns abbreviated stage name with Rich color markup
  └── Example: "[yellow]impling[/yellow]"

Step 2: format_lifecycle_with_status()
  └── Detects stage by substring matching
  └── Appends emoji indicators based on PR status
  └── Example: "[yellow]impling[/yellow] rocket-construction"

Step 3: plan_table.py rendering
  └── Places formatted string in fixed-width column (width=11)
  └── Textual silently truncates if content exceeds width
```

## Why This Matters

Partial fixes cause confusing bugs:

- Changing Step 1 abbreviations without updating Step 2 detection → emojis disappear
- Changing Step 2 indicator positioning without updating Step 3 width → emojis truncated
- Unit tests pass (string is correct) but visual display fails (column too narrow)

## File Locations

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display -->
<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, format_lifecycle_with_status -->
<!-- Source: src/erk/tui/widgets/plan_table.py, _setup_columns -->

Step 1 and Step 2: See `lifecycle.py` in `erk_shared/gateway/plan_data_provider/`
Step 3: See `_setup_columns()` in `src/erk/tui/widgets/plan_table.py`

## Verification

After modifying any step, verify the complete pipeline:
1. Run unit tests: `pytest tests/unit/plan_store/test_lifecycle_display.py`
2. Run visual verification: `erk dash` and inspect stage column display
```

---

### LOW Priority

#### 11. TUI testing coverage gap: display vs rendering

**Location:** `docs/learned/testing/tui-testing-gaps.md`
**Action:** CREATE
**Source:** [Impl] Session 867c9114, [PR #7852]

**Draft Content:**

```markdown
---
title: TUI Testing Gaps
read_when:
  - "TUI tests pass but display looks wrong"
  - "adding visual elements to TUI"
  - "debugging column truncation issues"
tripwires:
  - action: "after modifying TUI display logic, rendering, or layout"
    warning: "REQUIRED: Run `erk dash` to verify visual layout. Unit tests validate string formatting but cannot catch column width truncation."
    score: 5
---

# TUI Testing Gaps

Unit tests verify formatted strings are correct, but cannot catch column width truncation issues in the actual Textual rendering.

## The Gap

| What unit tests verify | What unit tests cannot verify |
|------------------------|-------------------------------|
| String content is correct | Column width accommodates content |
| Emoji positions in string | Emoji actually visible after truncation |
| Color markup is valid | Layout doesn't push content offscreen |

## Why This Happens

1. Unit tests check `format_lifecycle_with_status()` returns correct string
2. String is correct, e.g., "impling rocket-construction"
3. But Textual's `_setup_columns()` sets width=9
4. String needs width=10, so suffix emoji is silently truncated
5. Tests pass, but users see no emoji

## Mitigation

1. **Visual verification required**: After TUI layout changes, run `erk dash`
2. **Calculate widths explicitly**: Document column width calculations
3. **Consider integration tests**: For critical layout constraints, test with actual Textual rendering

## Example Failure

PR #7852 moved emojis from prefix to suffix. Tests passed (string was correct). User reported "draft statuses disappeared." Root cause: column width sized for old prefix format, suffix emojis were truncated.
```

---

#### 12. Dashboard column width update

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [Impl] Session c9098c54, [PR #7852]

**Draft Content:**

Update the stage column entry in the existing table or add a note:

```markdown
## Column Width Details

The stage column width changed from 9 to 11 characters in PR #7852:

| Column | Width | Calculation |
|--------|-------|-------------|
| stage | 11 | "impling" (7) + space (1) + emoji (2) + margin (1) |

This accommodates the longest stage abbreviation with emoji suffix indicators.
```

---

#### 13. Lifecycle stage display update

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [Impl] Session ec5ab77c, [PR #7852]

**Draft Content:**

Add note to the "Display Computation" section:

```markdown
### Display Abbreviations

For TUI space constraints, some stage names are abbreviated in display:

| Stage | Display | Reason |
|-------|---------|--------|
| implementing | impling | Column width constraint |
| implemented | impld | Column width constraint |

Other stages (planned, review) display their full names.

<!-- Source: erk_shared/gateway/plan_data_provider/lifecycle.py, compute_lifecycle_display -->
```

---

## Contradiction Resolutions

No contradictions detected between existing documentation and new insights from this PR.

---

## Stale Documentation Cleanup

No stale documentation detected. All referenced artifacts in existing docs were verified and exist in the codebase.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Emoji indicators disappear after UI repositioning

**What happened:** Moving emojis from prefix to suffix position caused them to disappear from the stage column.

**Root cause:** Column width was calculated for old prefix format. New suffix format with longer abbreviation exceeded width, and Textual silently truncated the suffix.

**Prevention:** Calculate visual display width including emojis (2 columns each). Verify longest case fits in column width. Always run `erk dash` to verify visual output.

**Recommendation:** TRIPWIRE (score 6) - added as tripwire candidate #3

### 2. Tests failing under xdist parallel execution

**What happened:** Test assertions about temp file cleanup failed intermittently in CI.

**Root cause:** Test scanned shared `tempfile.gettempdir()` for pattern-matched files. Concurrent xdist workers created matching files between before/after snapshots.

**Prevention:** Monkeypatch `tempfile.tempdir` to test-specific `tmp_path / "temp"` directory before any tempfile operations.

**Recommendation:** TRIPWIRE (score 7) - added as tripwire candidate #2

### 3. Stage detection breaks when display strings change

**What happened:** After changing abbreviations, emoji indicators stopped appearing on certain stages.

**Root cause:** `format_lifecycle_with_status()` detects stages via substring matching. Changing display names without updating detection logic caused silent failures.

**Prevention:** When changing display strings in `compute_lifecycle_display()`, always update detection logic in `format_lifecycle_with_status()` in the same commit.

**Recommendation:** TRIPWIRE (score 8) - added as tripwire candidate #1

### 4. Over-engineering test updates

**What happened:** Agent initially planned to update 26 individual test call sites with explicit parameters.

**Root cause:** Mechanical application of "no defaults" rule without considering cleaner alternatives.

**Prevention:** Check if a test helper with defaults would be cleaner before mass-editing test calls. Test infrastructure is exempt from production code constraints.

**Recommendation:** CONTEXT_ONLY - captured in false positive patterns doc

### 5. Accepting bot reviewer false positives

**What happened:** Agent initially considered addressing bot complaints about hardcoded strings and internal coupling.

**Root cause:** Bot reviewed without understanding PR intent (abbreviation was the goal, internal coupling was intentional).

**Prevention:** Systematically verify bot complaints against PR intent and git diff. Check for known false positive patterns before investing time.

**Recommendation:** TRIPWIRE (score 4) - added as tripwire candidate #5

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Stage detection by substring matching

**Score:** 8/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1, Affects multiple files +1)

**Trigger:** Before changing stage display names in compute_lifecycle_display()

**Warning:** CRITICAL: format_lifecycle_with_status() detects stages by substring matching. Changing display strings MUST update detection logic to match new substrings. Breaking this causes emoji indicators to silently not appear on correct stages.

**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the failure is completely silent - tests pass, but the visual output is wrong. Users discover the issue, not automated checks.

### 2. Shared temp directory scanning anti-pattern

**Score:** 7/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1)

**Trigger:** Before writing tests that scan temp directories or use tempfile operations

**Warning:** FORBIDDEN: Tests MUST NOT scan shared system directories (tempfile.gettempdir()) for pattern-matched files under parallel xdist execution. Monkeypatch tempfile.tempdir to tmp_path for isolation.

**Target doc:** `docs/learned/testing/tripwires.md`

This affects any test using tempfile operations and causes intermittent CI failures that are difficult to reproduce locally.

### 3. TUI column width calculation for emojis

**Score:** 6/10 (criteria: Non-obvious +2, Silent failure +2, Repeated pattern +1, External tool quirk +1)

**Trigger:** Before adding or repositioning emojis in TUI table columns

**Warning:** Emojis count as 2 visual columns in terminal display. Calculate width: max_text + space + (emoji_count x 2) + margin. Verify visually with `erk dash`; unit tests cannot catch truncation.

**Target doc:** `docs/learned/tui/tripwires.md`

Textual's silent truncation behavior makes this particularly dangerous. The code is correct but the output is wrong.

### 4. TUI changes require visual verification

**Score:** 5/10 (criteria: Non-obvious +2, Silent failure +2, Repeated pattern +1)

**Trigger:** After modifying TUI display logic, rendering, or layout

**Warning:** REQUIRED: Run `erk dash` to verify visual layout. Unit tests validate string formatting but cannot catch column width truncation, alignment issues, or color rendering problems.

**Target doc:** `docs/learned/tui/tripwires.md`

This is the meta-tripwire that catches any TUI-related issue that unit tests miss.

### 5. False positive detection for PR reviews

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)

**Trigger:** Before accepting automated reviewer comments on PRs

**Warning:** VERIFY: Check automated reviewer comments against PR intent and git diff. Common false positives: hardcoded UI constraints, internal module coupling, test helper defaults.

**Target doc:** `docs/learned/reviews/false-positive-patterns.md`

The 73% false positive rate observed in PR #7852 (8 of 11 threads) indicates this is a systematic issue worth documenting.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Three-way boolean validation for optional fields

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)

**Notes:** Pattern is subtle but localized to PR status checks. Not cross-cutting enough for high priority tripwire. Could be promoted if same pattern appears in other domains.

### 2. Scope boundary analysis for pre-existing issues

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)

**Notes:** Good practice but doesn't cause destructive failures. More of a workflow optimization than error prevention.

### 3. Lifecycle display pipeline awareness

**Score:** 2/10 (criteria: Cross-cutting +2)

**Notes:** Understanding the pipeline is important but the pattern itself isn't error-prone once documented. The specific tripwires for each step (detection, width) are more valuable than a meta-tripwire about the pipeline.

---

## Cornerstone Redirects (SHOULD_BE_CODE)

Two items belong in code artifacts rather than learned docs:

### 1. PullRequestInfo fields for status indicators

**Why SHOULD_BE_CODE:** Single-artifact API reference (method tables, signatures for one class) belongs in docstrings on that artifact, not learned docs.

**Recommended Location:** Add docstring to PullRequestInfo class documenting: checks_passing drives rocket, has_conflicts drives collision, review_decision drives check/cross, is_draft drives construction/eyes.

### 2. Test helper defaults exception

**Why SHOULD_BE_CODE:** Names specific pattern (test helpers) and scopes it to specific rule. Belongs in coding standards skill.

**Recommended Location:** Add clarification to dignified-python skill: "No default parameters in production code. Test helpers MAY use defaults to reduce boilerplate when all test callers would pass the same value."

---

## Open Questions for Human Review

1. **Test helper defaults exception**: Should dignified-python skill explicitly document that test helpers MAY use default parameters? PR #7852 author claimed exemption, but automated reviewers flagged it. Recommend: Yes, add explicit clarification.

2. **Emoji width calculation**: Should this be a standalone doc or merged into column-addition-pattern.md? Current decision: Addressed in lifecycle-indicators.md to keep context together.

3. **Lifecycle abbreviations**: Should this reference CLI abbreviated header conventions (chks, wt, st) for consistency? Current draft: Yes, includes cross-reference for consistency rationale.
