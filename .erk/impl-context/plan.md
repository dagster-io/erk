# Changelog Update Plan

## Context
Sync CHANGELOG.md unreleased section with 16 commits merged to master since last sync marker (b372dfbcc).

## Changes
Update `CHANGELOG.md` Unreleased section:

1. Update "As of" marker from `b372dfbcc` to `f5b9b5c50`
2. Add 8 new entries under existing category headers:

### Added (3 new entries)
- Add one-shot prompt modal to `erk dash` (`x` keybinding) for quick dispatch without leaving the TUI (a87c69bab)
- Add visible AI-generated summary to plan PRs, displayed above collapsed plan details for quick overview (bd69797ac)
- Show toast notification when learn plan is created during TUI landing (682827afc)

### Changed (3 new entries)
- Rename "Fix Conflicts Remote" to "Rebase Remote" in TUI and always perform rebase (fe5c1231c)
- Require `--summary` flag on `erk pr create` instead of auto-generating summaries (b9fc51011)
- Use LLM-generated branch name slugs for plan PRs, producing more descriptive branch names (f5b9b5c50)

### Fixed (1 new entry)
- Fix stale stack indicator showing incorrectly when parent PR is already merged (d04377e0d)

### Removed (1 new entry, new header)
- Remove erkdesk Electron desktop app and all references (0d58bd0b7)

## Verification
- Confirm "As of" marker updated to f5b9b5c50
- Confirm all 8 entries present under correct headers
- Confirm existing entries preserved unchanged
