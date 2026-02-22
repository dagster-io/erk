# Fix: erk dash TUI not displaying merge conflict state

## Context

PR #7850 has `mergeable: "CONFLICTING"` but the `erk dash` TUI shows no merge conflict indicator. This is a draft_pr mode issue — in issue-based mode, conflicts are visible via the separate PR column's emoji (`#7850 👀💥`), but in draft_pr mode that column doesn't exist.

## Root Cause (two bugs)

**Bug 1 — Stage gate excludes "implemented"**: `format_lifecycle_with_status()` in `lifecycle.py:119` returns early for "implemented" stage:
```python
if not is_implementing and not is_review:
    return lifecycle_display
```
The check `"implementing" in lifecycle_display` does NOT match "implemented". Since "implemented" = non-draft OPEN PR (exactly when merge conflicts matter most for merging), this is a critical gap.

**Bug 2 — Suffix placement invisible in truncated column**: Indicators are appended as suffixes (`"implemented 💥"`). The stage column is 9 chars wide. "implemented" (11 chars) already truncates to "implement" — any suffix is never visible.

## Solution

Rewrite `format_lifecycle_with_status()` to:
1. Add `is_implemented` detection, include it in `is_active_stage`
2. Move all indicators (💥, ✔, ❌) from **suffix** to **prefix** position so they survive column truncation

Result examples:
- `"[cyan]👀 💥 implemented[/cyan]"` → truncates to `👀 💥 imp` (both emojis visible)
- `"[yellow]🚧 💥 implementing[/yellow]"` → truncates to `🚧 💥 imp` (both visible)

## Changes

### 1. `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

Replace body of `format_lifecycle_with_status()` (lines 96-148). New approach:
- Parse Rich markup tags once, extracting raw stage text
- Build ordered prefix parts: draft/published emoji → conflict emoji → review decision emoji
- Reassemble with markup

Key logic:
```python
is_implemented = "implemented" in lifecycle_display and "implementing" not in lifecycle_display
is_active_stage = is_planned or is_implementing or is_implemented or is_review

parts: list[str] = []
if is_active_stage and is_draft is not None:
    parts.append("🚧" if is_draft else "👀")
if is_active_stage and has_conflicts is True:
    parts.append("💥")
if is_review:
    if review_decision == "APPROVED":
        parts.append("✔")
    elif review_decision == "CHANGES_REQUESTED":
        parts.append("❌")

prefix = " ".join(parts) + " "
return opening_tag + prefix + stage_text + closing_tag
```

### 2. `tests/unit/plan_store/test_lifecycle_display.py`

**Update 11 tests** — suffix → prefix positioning:
| Test | Old | New |
|---|---|---|
| `test_review_with_conflicts` | `"review 💥"` | `"💥 review"` |
| `test_review_approved` | `"review ✔"` | `"✔ review"` |
| `test_review_changes_requested` | `"review ❌"` | `"❌ review"` |
| `test_review_conflicts_and_changes_requested` | `"review 💥 ❌"` | `"💥 ❌ review"` |
| `test_review_conflicts_and_approved` | `"review 💥 ✔"` | `"💥 ✔ review"` |
| `test_implementing_with_conflicts` | `"implementing 💥"` | `"💥 implementing"` |
| `test_review_with_none_conflicts` | `"review ✔"` | `"✔ review"` |
| `test_plain_text_stage_appends_suffix` | `"review 💥 ✔"` | `"💥 ✔ review"` |
| `test_review_published_with_conflicts_shows_both` | `"👀 review 💥"` | `"👀 💥 review"` |
| `test_review_published_with_approved_shows_both` | `"👀 review ✔"` | `"👀 ✔ review"` |
| `test_implementing_draft_with_conflicts_shows_both` | `"🚧 implementing 💥"` | `"🚧 💥 implementing"` |

**Update 1 test** — planned now shows conflicts:
- `test_planned_stage_no_indicators` → rename to `test_planned_stage_shows_conflicts_not_review_decision`, expect `"[dim]💥 planned[/dim]"` (has_conflicts=True shows 💥, but review_decision is ignored for non-review stages)

**Add 4 new tests** for "implemented" stage:
- `test_implemented_with_conflicts` — `"[cyan]💥 implemented[/cyan]"`
- `test_implemented_no_conflicts` — unchanged `"[cyan]implemented[/cyan]"`
- `test_implemented_published_with_conflicts` — `"[cyan]👀 💥 implemented[/cyan]"`
- `test_implemented_ignores_review_decision` — no ✔/❌ for non-review stage

### Files NOT changed
- `plan_table.py` — stage column width of 9 is fine; prefix approach handles truncation
- `real.py` (data provider) — already correctly passes `has_conflicts` to `format_lifecycle_with_status()`
- `emoji.py` — already has correct `get_pr_status_emoji()` with conflict support

## Verification

1. `uv run pytest tests/unit/plan_store/test_lifecycle_display.py` — lifecycle tests
2. `uv run pytest tests/tui/` — TUI table tests (should be unaffected)
3. Manual: `erk dash -i` with a conflicting PR to confirm 💥 appears
