# Split commit into two separate PRs

## Context

Commit `f539937` on `plnd/migrate-to-batch-exec-02-27-1155` combines two unrelated changes:
1. Migrating exec callers to batch variants
2. Simplifying the TUI view bar

These should be two independent PRs.

## File groupings

**PR 1: Migrate exec callers to batch variants**
- `.claude/commands/erk/replan.md` — `close-pr` → `close-prs`, `add-plan-label` → `add-plan-labels`
- `.claude/commands/local/check-relevance.md` — `close-pr` → `close-prs`

**PR 2: Simplify TUI view bar**
- `src/erk/tui/widgets/view_bar.py` — remove clickable tabs, inline rendering
- `src/erk/tui/app.py` — remove `on_view_tab_clicked` handler
- `tests/tui/test_view_bar.py` — remove `TestBuildViewBarContent` and `TestViewBarTabRegions` classes
- `docs/learned/tui/status-indicators.md` — update docs

## Steps

1. Reset the current branch back to `origin/master` (undo the single commit)
2. Create branch 1, cherry-pick only the exec-batch changes, submit PR
3. Create branch 2, cherry-pick only the TUI view bar changes, submit PR

Concretely:

1. `git reset --hard HEAD~1` on this branch to undo the combined commit
2. Create first branch from `origin/master`, apply only the command file changes (2 files), commit and submit
3. Create second branch from `origin/master`, apply only the TUI changes (4 files), commit and submit

## Verification

- Each PR should have a clean diff touching only its respective files
- `gt` or `gh` PR list shows two separate PRs
