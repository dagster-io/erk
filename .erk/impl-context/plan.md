# Documentation Plan: Align erk plan list with erk dash layout and remove obsolete features

## Context

This implementation aligned the static CLI command `erk plan list` with the TUI dashboard (`erk dash`) by reusing `RealPlanDataProvider`, eliminating approximately 280 lines of duplicated data assembly logic. The work removed the obsolete `--runs` flag (workflow run columns now always shown), added clickable links for plan numbers, objectives, and PRs via OSC 8 terminal hyperlinks, and adapted column layout based on plan backend (github vs draft_pr).

The implementation sessions encountered a significant cross-cutting issue: Rich Console markup and Textual widget markup have different URL quoting requirements. Multiple sessions incorrectly applied Textual widget documentation to Rich Console code, causing terminal hyperlinks to break. This distinction is critical for any future code that generates clickable terminal output.

A future agent working with plan table rendering, CLI output formatting, or TUI-CLI code sharing would benefit from knowing: (1) how to reuse TUI data providers in CLI commands, (2) the critical distinction between Rich Console and Textual widget markup for hyperlinks, (3) the 6-step pattern for adding fields to widely-used frozen dataclasses, and (4) test fixture patterns for backend-dependent behavior.

## Raw Materials

PR #7937

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 21 |
| Contradictions to resolve | 1 |
| Tripwire candidates (score >= 4) | 6 |
| Potential tripwires (score 2-3) | 3 |

## Contradiction Resolutions

### 1. Rich Console vs Textual Widget Markup Quoting

**Existing doc:** `docs/learned/textual/quirks.md` (lines 154-180)
**Conflict:** The existing document explains URL quoting requirements for Textual widgets (`Label(..., markup=True)`), but agents misapplied this guidance to Rich Console markup. Sessions 95abc75c and ce62ecac both made this mistake, adding quotes to `[link=...]` markup which broke OSC 8 terminal hyperlinks.
**Resolution:** Update `docs/learned/textual/quirks.md` with explicit scope boundary and create new `docs/learned/cli/rich-console-markup.md` documenting Rich Console's unquoted URL requirement.

## Stale Documentation Cleanup

No stale documentation was detected. All referenced artifacts in existing docs were verified to exist.

## Documentation Items

### HIGH Priority

#### 1. Rich Console vs Textual Markup Quoting [CONTRADICTION]

**Location:** `docs/learned/cli/rich-console-markup.md` (CREATE) + `docs/learned/textual/quirks.md` (UPDATE)
**Action:** CREATE + UPDATE
**Source:** [Impl] Sessions 7b3483dc, 95abc75c, ce62ecac

**Draft Content:**

```markdown
# Rich Console Markup for Clickable Links

Rich Console and Textual widgets use similar markup syntax but have **different URL parsing rules**.

## URL Quoting Rules

**Rich Console** (`rich.console.Console`, `rich.table.Table`):
- Use UNQUOTED URLs: `[link=https://example.com]text[/link]`
- Quotes become literal characters in OSC 8 escape sequences

**Textual Widgets** (`Label(..., markup=True)`):
- May require quotes in certain contexts
- See `docs/learned/textual/quirks.md`

## Why Quotes Break Rich Links

Rich's parsing flow (traced from source):
1. `markup.py:99` extracts raw value after `=` as parameters
2. `style.py:515` splits by whitespace
3. `style.py:543` assigns next word verbatim as URL
4. URL inserted into OSC 8 sequence: `\x1b]8;id={id};{URL}\x1b\`

With quotes: `"https://..."` becomes the literal URL (invalid)
Without quotes: `https://...` becomes the URL (valid)

## Reference Implementation

See `src/erk/cli/commands/view/view_cmd.py` for working unquoted URL example.

## Testing

Verify links work by Cmd+click in terminal (iTerm2, Kitty, etc.). Automated tests may not catch OSC 8 rendering issues.
```

**Update for textual/quirks.md:**
Add scope boundary at top:
```markdown
> **SCOPE**: These quirks apply to Textual **widgets** only (e.g., `Label(..., markup=True)`).
> For Rich Console markup patterns, see `docs/learned/cli/rich-console-markup.md`.
```

---

#### 2. Ternary Operator and Short-Circuit Guidelines

**Location:** `docs/learned/reference/ternary-guidelines.md`
**Action:** CREATE
**Source:** [PR #7937] - 3 automated bot violations

**Draft Content:**

```markdown
# Ternary Operator and Short-Circuit Guidelines

Guidelines for when ternary operators and short-circuit evaluation are acceptable versus when explicit if/else should be used.

## Acceptable Uses

### Simple None/Falsy Checks
```python
value = x if x is not None else default
text = content or "N/A"
```

### Two-option Fallbacks
```python
display = primary or secondary
```

## Forbidden Uses

### Ternaries Inside f-strings
Parsing complexity makes these hard to read:
```python
# FORBIDDEN
f"Status: {status if status else 'unknown'}"

# USE INSTEAD
status_text = status if status else "unknown"
f"Status: {status_text}"
```

### Chained Short-Circuits with 3+ Options
```python
# FORBIDDEN
result = a or b or c or d

# USE INSTEAD
if a:
    result = a
elif b:
    result = b
elif c:
    result = c
else:
    result = d
```

### Nested Ternaries
```python
# FORBIDDEN
x = a if cond1 else (b if cond2 else c)
```

## Rationale

Explicit if/else improves readability and makes debugging easier. Ternaries save vertical space but cost horizontal complexity.
```

---

#### 3. CLI Reusing TUI Data Infrastructure

**Location:** `docs/learned/architecture/cli-tui-data-sharing.md`
**Action:** CREATE
**Source:** [Impl] Session e4b21715, Diff analysis

**Draft Content:**

```markdown
# CLI Reusing TUI Data Infrastructure

Pattern for CLI commands that would otherwise duplicate TUI data assembly logic.

## When to Apply

Apply when a CLI command needs to display the same data as a TUI component. Signs of opportunity:
- CLI and TUI have similar output columns
- Both need the same GitHub API calls
- Both apply similar data transformations

## Pattern

Import and reuse TUI data providers in CLI commands.

### Example: erk plan list

Before: `list_cmd.py` had `_build_plans_table()` with ~280 lines of duplicated data assembly
After: `list_cmd.py` imports `RealPlanDataProvider.fetch_plans()` from `erk_shared.gateway`

Benefits:
- Eliminated ~280 lines of duplicate logic
- CLI and TUI always show consistent data
- Single source of truth for data transformations
- Reduces maintenance burden

## Implementation Notes

- Import from `erk_shared.gateway` packages
- Both surfaces should use same row data types (e.g., `PlanRowData`)
- Column rendering can differ between CLI (static Rich Table) and TUI (DataTable widget)

## Reference

See `src/erk/cli/commands/plan/list_cmd.py` for implementation using `RealPlanDataProvider`.
```

---

#### 4. Backend-Dependent Column Layout Pattern

**Location:** `docs/learned/architecture/plan-backend-column-layout.md`
**Action:** CREATE
**Source:** [Impl] Session e4b21715, Diff analysis

**Draft Content:**

```markdown
# Backend-Dependent Column Layout Pattern

`erk plan list` and `erk dash` adapt their column structure based on the configured plan backend.

## Layout Differences

### GitHub Backend (`github`)
- First column: `plan` (issue number)
- Includes: `obj`, `loc`, `branch`, `created`, `author`, `cmts`
- Separate `pr` column when applicable

### Draft PR Backend (`draft_pr`)
- First column: `pr` (PR number)
- Adds: `stage`, `sts` columns
- No separate PR column (PR is the plan)

## Implementation

See `PlanDataTable._setup_columns()` in TUI and `_build_static_table()` in CLI.

Both surfaces call `get_plan_backend()` to determine layout.

## Testing Requirements

Tests that verify column output MUST explicitly set the plan backend.

**CRITICAL**: Use direct `os.environ` manipulation in test fixtures, not monkeypatch:

```python
@pytest.fixture(autouse=True)
def _force_github_plan_backend():
    import os
    original = os.environ.get("ERK_PLAN_BACKEND")
    os.environ["ERK_PLAN_BACKEND"] = "github"
    yield
    if original is None:
        os.environ.pop("ERK_PLAN_BACKEND", None)
    else:
        os.environ["ERK_PLAN_BACKEND"] = original
```

See `tests/commands/dash/conftest.py` for reference.
```

---

#### 5. Frozen Dataclass Field Addition Checklist

**Location:** `docs/learned/architecture/frozen-dataclass-field-addition.md`
**Action:** CREATE
**Source:** [Impl] Session ce62ecac (TypeError from missing status_display field)

**Draft Content:**

```markdown
# Frozen Dataclass Field Addition Checklist

When adding required fields to frozen dataclasses used across the codebase (e.g., `PlanRowData`), follow this 6-step checklist.

## Checklist

1. **Add field to dataclass definition**
   - Place in logical position (group related fields)
   - Use appropriate type annotation with nullable marker if optional

2. **Update real provider**
   - Add computation logic to build and pass the new field value
   - See `RealPlanDataProvider._build_row_data()` for example

3. **Update fake/test helper**
   - Mirror the real provider's field addition
   - See `FakePlanDataProvider.make_plan_row()` for example

4. **Grep for all direct constructor calls**
   - Search: `ClassName(` (e.g., `PlanRowData(`)
   - Update every call site to include the new field

5. **Update tests**
   - Add new field to test assertions
   - Update test data factories/fixtures

6. **Update field validation tests**
   - Find tests that assert on expected field sets
   - Add new field to expected field lists

## Why This Matters

Frozen dataclasses require all fields at construction time. Missing a constructor call site causes `TypeError: __init__() missing required positional argument`.

## Example

Adding `objective_url` field to `PlanRowData`:
- Updated `src/erk/tui/data/types.py` (definition)
- Updated `packages/erk-shared/.../real.py` (real provider)
- Updated `packages/erk-shared/.../fake.py` (fake provider)
- Grepped for `PlanRowData(` and updated all test files
```

---

#### 6. Plan Backend Configuration in Test Fixtures

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session e4b21715 (26 tests failed after implementation)

**Draft Content to Add:**

```markdown
## Plan Backend Test Configuration

**Trigger:** Writing tests for code that depends on `get_plan_backend()`

**Warning:** Add autouse fixture to force `ERK_PLAN_BACKEND` using direct `os.environ` manipulation (NOT monkeypatch). Backend defaults to `draft_pr`, changing column layout unexpectedly.

**Why:** `monkeypatch.setenv()` doesn't reliably propagate to `get_plan_backend()` calls in autouse fixtures. Direct `os.environ` manipulation with generator cleanup works.

**Reference:** `tests/commands/dash/conftest.py`
```

---

### MEDIUM Priority

#### 7. strip_rich_markup() Shared Utility

**Location:** `docs/learned/architecture/shared-utilities.md`
**Action:** CREATE
**Source:** [Diff] - New function in display_utils.py

**Draft Content:**

```markdown
# Shared Utility Functions

Utility functions extracted to `src/erk/core/display_utils.py` for use across CLI and TUI.

## strip_rich_markup()

Removes Rich markup tags from strings for plain text output.

**Location:** `src/erk/core/display_utils.py`

**Purpose:**
- Strip `[tag]...[/tag]` syntax
- Strip `[link=...]...[/link]` syntax
- Return plain text for contexts that don't support markup

**Usage:**
```python
from erk.core.display_utils import strip_rich_markup

plain = strip_rich_markup("[bold]Hello[/bold]")  # Returns "Hello"
```

**Pattern:** When both CLI and TUI need the same string transformation, extract to `display_utils.py` rather than duplicating regex patterns.
```

---

#### 8. Update PlanRowData Documentation

**Location:** `docs/learned/tui/plan-row-data.md`
**Action:** UPDATE
**Source:** [Diff] - New objective_url field

**Draft Content to Add:**

Add to Objective Info table:
```markdown
| Field | Type | Nullability | Purpose |
|-------|------|-------------|---------|
| objective_url | str | nullable | URL for clickable objective link |
```

---

#### 9. Environment Variable Patching in Conftest

**Location:** `docs/learned/testing/env-var-patching.md`
**Action:** CREATE
**Source:** [Impl] Session e4b21715 (monkeypatch.setenv didn't propagate)

**Draft Content:**

```markdown
# Environment Variable Patching in Conftest Fixtures

When pytest's `monkeypatch.setenv()` doesn't work in autouse fixtures, use direct `os.environ` manipulation.

## When Monkeypatch Fails

- Autouse fixtures with scope issues
- Click CliRunner subprocess calls
- Module import timing issues

## Pattern: Direct os.environ with Cleanup

```python
@pytest.fixture(autouse=True)
def _force_env_var():
    import os
    original = os.environ.get("ENV_VAR_NAME")
    os.environ["ENV_VAR_NAME"] = "desired_value"
    yield
    if original is None:
        os.environ.pop("ENV_VAR_NAME", None)
    else:
        os.environ["ENV_VAR_NAME"] = original
```

## Reference

See `tests/commands/dash/conftest.py` for `_force_github_plan_backend` fixture.

## Why This Works

Direct `os.environ` manipulation persists across test setup phases and subprocess calls, while monkeypatch may not propagate depending on fixture evaluation order.
```

---

#### 10. Rich Table Column Width Calculations

**Location:** `docs/learned/cli/rich-table-column-widths.md`
**Action:** CREATE
**Source:** [Impl] Session e4b21715 (emoji truncation), session 53b6be53 (underline padding)

**Draft Content:**

```markdown
# Rich Table Column Width Calculations

Rich Table with `no_wrap=True` strictly truncates content to the `width=` parameter.

## Width Requirements

1. **Header length:** `width >= len(header_text)`
2. **Emoji content:** Add 2 display cells per emoji

## Example

Column displaying `#204 👀💥`:
- `#204 ` = 5 cells
- `👀` = 2 cells
- `💥` = 2 cells
- Total = 9 cells
- Column width should be >= 10 (padding)

## Testing

Add assertions checking column headers appear in output:
```python
assert "remote-impl" in result.output  # Catches truncation to "remote-im..."
```

## Column vs Text Styling

When using `Text(content, style="underline")`, the style extends to Rich's column padding. For links without styled padding, use `[link=URL]text[/link]` markup instead.
```

---

#### 11. Test Helper Updates When Return Types Change

**Location:** `docs/learned/testing/test-helper-updates.md`
**Action:** CREATE
**Source:** [Impl] Session 95abc75c (test failure from _text_to_str not handling strings)

**Draft Content:**

```markdown
# Test Helper Updates When Return Types Change

When implementation changes return types, test helpers that process those types need corresponding updates.

## Pattern

1. Implementation changes return type (e.g., `Text` objects -> markup strings)
2. Tests pass type to helper function (e.g., `_text_to_str()`)
3. Helper fails because it only handles old type

## Prevention

When changing return types:
1. Grep for test helpers that process the old type
2. Update helpers to handle both old and new types (or just new type)
3. Consider adding type checks in helpers

## Example

`_text_to_str()` originally only handled `Text.plain`:
```python
# Before: only handled Text
def _text_to_str(obj):
    return obj.plain

# After: handles both
def _text_to_str(obj):
    if isinstance(obj, Text):
        return obj.plain
    return strip_rich_markup(str(obj))
```
```

---

#### 12. Pre-Existing Test Failure Detection

**Location:** `docs/learned/testing/pre-existing-test-failures.md`
**Action:** CREATE
**Source:** [Impl] Session 95abc75c

**Draft Content:**

```markdown
# Pre-Existing Test Failure Detection

Workflow for distinguishing new test failures from pre-existing ones.

## Git Stash Technique

```bash
# Stash your changes
git stash

# Run tests to see baseline failures
pytest path/to/tests

# Restore your changes
git stash pop
```

If tests fail with stashed changes, those failures are pre-existing.

## When to Use

- Multiple test failures after implementation
- Uncertainty whether failures are from your changes
- Before spending time debugging "new" failures

## Benefits

- Saves time by identifying inherited test debt
- Helps decide whether to fix or skip pre-existing issues
- Documents baseline state for later cleanup
```

---

#### 13. ANSI Escape Sequence Analysis for Terminal Debugging

**Location:** `docs/learned/cli/terminal-debugging.md`
**Action:** CREATE
**Source:** [Impl] Session 53b6be53

**Draft Content:**

```markdown
# ANSI Escape Sequence Analysis for Terminal Debugging

When debugging terminal rendering issues (spacing, colors, links), analyze raw ANSI output rather than mental code tracing.

## Technique

Use `repr()` on Console output to see raw escape codes:

```python
from rich.console import Console
from io import StringIO

buffer = StringIO()
console = Console(file=buffer, force_terminal=True)
console.print("[cyan underline]#7944[/]")
print(repr(buffer.getvalue()))
# Output: '\x1b[4;36m#7944 \x1b[0m\n'
```

## What to Look For

- `\x1b[4;36m` = underline + cyan
- `\x1b[0m` = reset
- `\x1b]8;;URL\x1b\\` = OSC 8 hyperlink start
- Extra spaces indicate padding issues

## Creating Minimal Reproductions

Before diving into codebase:
1. Create minimal Rich table example
2. Print raw ANSI codes
3. Validate hypothesis about root cause
4. Then implement fix

## Reference

Session 53b6be53 used this technique to diagnose underline extending to padding spaces in Rich tables.
```

---

#### 14. Update Dashboard Columns Documentation

**Location:** `docs/learned/tui/dashboard-columns.md`
**Action:** UPDATE
**Source:** [Diff] - CLI now mirrors TUI layout

**Draft Content to Add:**

```markdown
## CLI Alignment

`erk plan list` now mirrors the TUI column layout:
- Both use same `RealPlanDataProvider`
- Both adapt to backend (github vs draft_pr)
- Column changes affect both surfaces

When modifying plan table columns, update both:
- `src/erk/cli/commands/plan/list_cmd.py`
- `src/erk/tui/widgets/plan_table.py`
```

---

#### 15. TUI/CLI Style Consistency Pattern

**Location:** `docs/learned/cli/tui-cli-mirroring.md`
**Action:** CREATE
**Source:** [Impl] Session 53b6be53

**Draft Content:**

```markdown
# TUI/CLI Style Consistency Pattern

`list_cmd.py` (CLI) and `plan_table.py` (TUI) mirror each other's styling logic for plan display.

## Pattern

Both files have:
- `_row_to_values()` or `_row_to_static_values()` methods
- Similar Rich markup handling
- Same column value transformations

## When Fixing Visual Bugs

If fixing a visual issue in one file, check the other:

| CLI Location | TUI Location |
|--------------|--------------|
| `src/erk/cli/commands/plan/list_cmd.py` | `src/erk/tui/widgets/plan_table.py` |

Both may need the same fix.

## Reference

Session 53b6be53 identified that underline padding issue affected both surfaces because they used identical `Text(style="cyan underline")` patterns.
```

---

### LOW Priority

#### 16. Worktree Branch Naming Pattern

**Location:** `docs/learned/architecture/worktree-branch-naming.md`
**Action:** CREATE or UPDATE
**Source:** [Impl] Session e4b21715

**Draft Content:**

```markdown
# Worktree Branch Naming Pattern

`extract_leading_issue_number()` expects branch names matching specific patterns for worktree detection.

## Required Patterns

- `P{issue_number}-{slug}` (erk-plan branches)
- `{issue_number}-{slug}` (general pattern)

## Testing Implications

Tests using generic branch names like `"feature-branch"` fail worktree detection.

Use: `"P950-feature-branch"` or `"1234-feature"` in tests involving:
- `_build_worktree_mapping()`
- `extract_leading_issue_number()`

## Reference

See `src/erk/core/branch_utils.py` for `extract_leading_issue_number()` implementation.
```

---

#### 17. Import-Time Side Effects Anti-Pattern

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE (add to anti-patterns section)
**Source:** [Impl] Session e4b21715 (ImportError from plan/__init__.py)

**Draft Content to Add:**

```markdown
## Import-Time Side Effects

**Anti-pattern:** `Path.cwd()`, I/O, or global state initialization in `__init__.py`

**Why it breaks tests:** When monkeypatch tries to load a module for patching, side effects execute immediately, potentially causing:
- `ImportError` from unmet dependencies
- Path resolution failures
- State pollution between tests

**Prevention:**
- Use lazy initialization
- Move side effects to function entry points
- Keep `__init__.py` files minimal (empty preferred)

**Example:** `erk/cli/commands/plan/__init__.py` calling `Path.cwd()` at import time broke test imports.
```

---

#### 18. OSC 8 Hyperlink Support

**Location:** `docs/learned/cli/output-styling.md`
**Action:** UPDATE
**Source:** [Impl] Sessions 7b3483dc, ce62ecac

**Draft Content to Add:**

```markdown
## OSC 8 Terminal Hyperlinks

Rich's `[link=URL]text[/link]` markup creates OSC 8 escape sequences for clickable terminal links.

### Format

```
\x1b]8;id={id};{URL}\x1b\\text\x1b]8;;\x1b\\
```

### Terminal Compatibility

Works in: iTerm2, Kitty, Hyper, Windows Terminal (recent versions)
Does not work in: basic terminals, older terminal emulators

### Testing

- Cmd+click (Mac) or Ctrl+click in terminal to verify
- Automated tests may not catch broken links
- Use raw ANSI output analysis for debugging

### Common Mistake

NEVER quote URLs: `[link="https://..."]` breaks links.
Use: `[link=https://...]` (unquoted)
```

---

#### 19. Column Count Test Documentation Staleness

**Location:** `docs/learned/testing/test-comment-staleness.md`
**Action:** CREATE
**Source:** [Impl] Session 95abc75c

**Draft Content:**

```markdown
# Test Comment Staleness

Test comments listing expected values (columns, fields, etc.) can become stale when code changes.

## Example

Comment listed 15 columns for draft_pr mode, actual code had 16 (missing `sts` column).

## Prevention

When adding columns/fields:
1. Search for test comments listing column/field names
2. Update comments to match new count
3. Consider moving counts into assertion messages:
   ```python
   assert len(columns) == 16, f"Expected 16 columns, got {len(columns)}"
   ```

## Better Pattern

Include counts in test names or assertions rather than comments:
```python
def test_draft_pr_mode_has_16_columns():
    ...
```
```

---

#### 20. Test Assertion Resilience

**Location:** `docs/learned/testing/stable-test-assertions.md`
**Action:** CREATE
**Source:** [Diff] - tests/commands/plan/test_list.py migration

**Draft Content:**

```markdown
# Test Assertion Resilience

Prefer stable identifiers over display text in test assertions.

## Pattern

| Less Stable | More Stable |
|-------------|-------------|
| `assert "Issue 1" in output` | `assert "#1" in output` |
| `assert "My Plan Title" in output` | `assert "#7937" in output` |

## Why

Display text changes more frequently than IDs:
- Column layout changes
- Formatting changes
- Internationalization

IDs are stable identifiers that survive presentation changes.

## Example

Old pattern (fragile):
```python
assert "Issue 1" in result.output
assert "Issue 2" in result.output
```

New pattern (resilient):
```python
assert "#1" in result.output
assert "#2" in result.output
```
```

---

#### 21. Visual Bug Debugging Process

**Location:** `docs/learned/testing/visual-bug-debugging.md`
**Action:** CREATE
**Source:** [Impl] Session 53b6be53

**Draft Content:**

```markdown
# Visual Bug Debugging Process

Workflow for debugging visual/terminal rendering issues.

## Process

1. **Request screenshot** if user doesn't provide one
2. **Create minimal reproduction** - small Rich table example
3. **Analyze ANSI output** - use `repr()` on console output
4. **Validate fix approach** before full implementation
5. **Check mirrored surfaces** - CLI and TUI may have same bug

## Anti-Pattern

Spending excessive time tracing through code mentally without creating a reproduction case.

## Example

Session 53b6be53 spent significant time (lines 5-619) exploring code before creating minimal reproduction at line 623. The reproduction immediately revealed the root cause (underline extending to padding).

## Reference

See `docs/learned/cli/terminal-debugging.md` for ANSI analysis techniques.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Broken Terminal Hyperlinks from URL Quoting

**What happened:** Added double quotes around URLs in Rich `[link=...]` markup based on Textual widget documentation
**Root cause:** Rich Console parses URLs differently than Textual widgets - quotes become literal characters in OSC 8 escape sequences
**Prevention:** Always use unquoted URLs in Rich Console markup: `[link=https://...]` not `[link="https://..."]`. Test Cmd+click in terminal.
**Recommendation:** TRIPWIRE - Critical cross-cutting issue affecting all clickable link rendering

### 2. Tests Failing After Column Refactor

**What happened:** 26 tests failed after implementing backend-dependent column layout
**Root cause:** `get_plan_backend()` returns `"draft_pr"` by default, changing column layout unexpectedly
**Prevention:** Add autouse fixture forcing `ERK_PLAN_BACKEND` to known value using direct `os.environ` (not monkeypatch)
**Recommendation:** TRIPWIRE - Affects all tests that verify plan table output

### 3. Misapplied Documentation Guidance

**What happened:** Applied Textual widget markup rules to Rich Console code
**Root cause:** Documentation scope not clear - "Textual quirks" sounds general but applies only to widgets
**Prevention:** Verify library scope (Textual vs Rich) and API surface (widget vs console) before applying patterns
**Recommendation:** ADD_TO_DOC - Update textual/quirks.md with explicit scope boundary

### 4. Test Helper Doesn't Handle New Return Type

**What happened:** `_text_to_str()` helper failed when implementation changed from Text objects to markup strings
**Root cause:** Helper only handled `Text.plain`, not string values
**Prevention:** When changing return types, grep for test helpers and update them
**Recommendation:** ADD_TO_DOC - Testing pattern documentation

### 5. Import Failures in Conftest

**What happened:** `import erk.cli.commands.plan.list_cmd` caused ImportError
**Root cause:** `plan/__init__.py` has side effects (`Path.cwd()`) at import time
**Prevention:** Avoid I/O and global state in `__init__.py`, use lazy initialization
**Recommendation:** ADD_TO_DOC - Add to architecture tripwires

### 6. Complex Ternary Expressions in Code Review

**What happened:** 3 automated bot violations for ternary/short-circuit patterns in PR #7937
**Root cause:** Using ternaries inside f-strings and chained short-circuits with 3+ options
**Prevention:** Use explicit if/else for complex conditionals
**Recommendation:** TRIPWIRE - Cross-cutting code style issue

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Rich Console Markup URL Quoting

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using `[link=...]` markup in Rich Console output
**Warning:** Use unquoted URLs: `[link=https://...]` NOT `[link="https://..."]`. Quotes break OSC 8 hyperlinks. See `docs/learned/cli/rich-console-markup.md`
**Target doc:** `docs/learned/architecture/tripwires.md` or `docs/learned/cli/tripwires.md`

This issue caused broken hyperlinks in multiple sessions. The failure is silent - links appear styled but don't work when clicked. Three implementation sessions (7b3483dc, 95abc75c, ce62ecac) hit this issue before the correct pattern was established.

### 2. Ternary Operators in f-strings and Chained Short-Circuits

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before using ternary operators or short-circuit evaluation
**Warning:** Avoid ternaries inside f-strings and chained short-circuits with 3+ options. Use explicit if/else for clarity. See `docs/learned/reference/ternary-guidelines.md`
**Target doc:** `docs/learned/architecture/tripwires.md`

PR #7937 had 3 automated bot violations for this pattern. The rule is non-obvious because simple ternaries are acceptable - it's the complex cases (inside f-strings, 3+ chained options) that are forbidden.

### 3. Plan Backend Configuration in Tests

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before writing tests that depend on `get_plan_backend()`
**Warning:** Add autouse fixture to force `ERK_PLAN_BACKEND` using direct `os.environ` manipulation (NOT monkeypatch). Backend defaults to `draft_pr`, changing column layout. See `docs/learned/testing/tripwires.md`
**Target doc:** `docs/learned/testing/tripwires.md`

Session e4b21715 had 26 test failures because the default backend produced different column layout than expected. Multiple monkeypatch approaches failed before direct `os.environ` manipulation worked.

### 4. CLI Reusing TUI Data Infrastructure

**Score:** 4/10 (Cross-cutting +2, Destructive potential +2)
**Trigger:** Before implementing CLI commands that duplicate TUI functionality
**Warning:** Check if TUI data providers can be reused. Example: `RealPlanDataProvider` eliminated ~280 lines of duplicate logic in `erk plan list`. See `docs/learned/architecture/cli-tui-data-sharing.md`
**Target doc:** `docs/learned/architecture/tripwires.md`

The original `list_cmd.py` had ~280 lines of duplicated data assembly logic. Reusing `RealPlanDataProvider` ensures CLI and TUI always show consistent data.

### 5. Backend-Dependent Column Layout

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before modifying plan list or dash column output
**Warning:** Columns adapt based on plan backend (github vs draft_pr). Force backend in tests. Update both CLI and TUI together. See `docs/learned/architecture/plan-backend-column-layout.md`
**Target doc:** `docs/learned/testing/tripwires.md`

The column layout differs significantly between backends. Tests that don't control the backend will have unpredictable failures.

### 6. Frozen Dataclass Field Addition

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before adding required fields to frozen dataclasses used across codebase
**Warning:** Follow 6-step checklist: grep for all constructor calls, update real/fake providers, update tests. See `docs/learned/architecture/frozen-dataclass-field-addition.md`
**Target doc:** `docs/learned/architecture/tripwires.md`

Session ce62ecac encountered `TypeError: __init__() missing required positional argument` because not all constructor call sites were updated.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. strip_rich_markup() Utility Duplication

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Already extracted to shared location (`display_utils.py`). May not need tripwire if the pattern of using shared utilities is well-established. Could be promoted if duplication recurs.

### 2. Environment Variable Patching in Conftest

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to pytest fixtures with autouse and Click CliRunner. May be too narrow for a general tripwire. Could be promoted if more cases emerge where monkeypatch fails.

### 3. TUI/CLI Style Consistency

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Affected limited code area (`list_cmd.py` + `plan_table.py`). May not be broad enough for general tripwire since it's specific to plan table rendering. Could be promoted if more surfaces need mirroring.
