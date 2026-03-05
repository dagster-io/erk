# Colorize Objective Nodes Screen

## Context

The objective nodes detail modal (`b` keybinding) currently strips Rich markup from stage and status columns, making them plain text. The user wants:
1. Stage column to show "merged"/"closed" with proper colors (green/dim red) instead of plain text
2. More emojis and visual appeal, matching the style of the main `erk dash` PR list

## File to Modify

`src/erk/tui/screens/objective_nodes_screen.py`

## Changes

### 1. Use `Text.from_markup()` instead of `strip_rich_markup()` for colored columns

In `_build_table_rows()`, the PR-enriched columns currently strip Rich markup (line 71). Change to preserve colors:

- **stage**: Use `Text.from_markup(pr_data.lifecycle_display)` instead of `strip_rich_markup()`
- **status (sts)**: Already uses `pr_data.status_display` directly — keep as-is
- **run-id**: Use `Text.from_markup(pr_data.run_id_display)` to preserve cyan coloring
- **run emoji**: Extract from `pr_data.run_state_display` using `Text.from_markup()`
- **chks**: Use `Text.from_markup(pr_data.checks_display)` to preserve check colors

### 2. Colorize node status symbols with emojis

Replace plain ASCII `_STATUS_SYMBOLS` characters with colored `Text` objects:
- `✓` (done) → `Text("✅", style="green")` or just `"✅"`
- `▶` (in_progress) → `Text("🚀", style="yellow")` or contextual emoji
- `○` (pending) → keep dim or use `Text("○", style="dim")`
- `⊘` (blocked) → `Text("⊘", style="red")`
- `◐` (planning) → `Text("◐", style="magenta")`

### 3. Colorize the node ID column

- Next node (`>>>` prefix): Use `Text(id_cell, style="bold yellow")` to highlight
- Regular nodes: Use `Text(id_cell, style="cyan")`

### 4. Colorize the PR number column

- PR numbers: `Text(f"#{pr_num}", style="cyan")`
- No PR: keep as `"-"`

### 5. Colorize description column

- Use `Text(desc, style="white")` for node descriptions (or leave default)
- Phase headers already use `style="bold"` — keep as-is

### 6. Widen stage column

The `stage` column width (currently 8) may need bumping to ~10 to accommodate "merged" + emoji indicators from `lifecycle_display`.

## Implementation Notes

- `Text.from_markup()` converts Rich markup strings like `[green]merged[/green]` into styled `Text` objects that Textual's DataTable renders correctly
- The main dash table (`plan_table.py:337`) also strips markup for stage — this is the same pattern, but we're improving just the nodes screen per request
- Import `Text` from `rich.text` (already imported)
- Remove unused `strip_rich_markup` import if all usages are replaced

## Verification

1. Run `erk dash -i`, navigate to Objectives tab, select an objective with merged/closed PRs, press `b`
2. Verify stage column shows colored text: green "merged", dim red "closed", yellow "impl"
3. Verify status emojis render (🚧, 👀, 💥, etc.)
4. Verify node status symbols are colorized
5. Run unit tests: `pytest tests/tui/`
