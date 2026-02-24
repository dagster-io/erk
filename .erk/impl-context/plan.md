# CHANGELOG.md Update Plan

## Context
Syncing CHANGELOG.md Unreleased section with 35 commits since f089a0abe. User reviewed the proposal and provided adjustments.

## Changes to Apply

Update "As of" marker from `f089a0abe` to `36e6f5d54`.

### Added (4 new entries)
- Add `erk plan duplicate-check` for semantic duplicate detection using LLM inference (d3fa2215)
- Add "blockers" column to TUI Objectives dashboard with clickable plan numbers (1ce603c0)
- Add `-d` and `-u` short aliases for `--down` and `--up` flags in `erk land` (152083a2)
- Add diagnostics for dispatch metadata failures with improved TUI feedback (9d8266be)

### Changed (3 new entries)
- Convert TUI dispatch commands from blocking modals to non-blocking toast+worker pattern (fd8a03c7)
- Remove backend label from statusline output (bc4f3263)
- Remove non-slot worktree after landing instead of leaving detached HEAD state (a6370895)

### Fixed (6 new entries)
- Fix objective update after landing for `plnd/` branches (36e6f5d5)
- Fix `erk br co --for-plan` stacking plan branches on current branch instead of trunk (febff7a7)
- Fix `erk land` crash when run from root worktree (8c1acc03)
- Fix session discovery for draft-PR plans by using header_fields (ae2d5dca)
- Fix `erk plan check` for draft-PR plan format and simplify branch force-update logic (d315ce47)
- Fix rocket emoji appearing on draft PRs in lifecycle display (71044645, 45a550fb)

### Removed (1 new entry)
- Remove `plan_backend` parameter and collapse dead github-backend code branches (3acaff21)

### Filtered (20 commits)
Internal infrastructure, docs, rolled-up commits, CI workflows, plus user-requested filters:
- `436b27238` (plan migration command deletion) - filtered per user request
- `e46c14dfb` (ModuleNotFoundError fix for renamed module) - filtered per user request

## File Modified
- `CHANGELOG.md` — update As-of marker, append entries under existing category headers

## Verification
- Read the updated Unreleased section to confirm formatting and completeness
