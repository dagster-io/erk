# Changelog Update Plan

## Context
Syncing CHANGELOG.md Unreleased section with 22 commits since marker 104f87771. User has reviewed and approved the categorization with adjustments.

## Changes to CHANGELOG.md

Update `<!-- As of 104f87771 -->` → `<!-- As of f089a0abe -->`

### Added (3 new entries appended after existing)
- Bundle missing capability workflows (one-shot, pr-address, pr-fix-conflicts) for external dispatch (509290e)
- Add local review marker to skip CI reviews when local code review passes (2bbcbfc)
- Add stacked PR emoji indicator to dashboard for PRs targeting non-master branches (ddd6360)

### Changed (7 new entries appended after existing)
- Fire-and-forget workflow dispatch — TUI remote operations return immediately instead of blocking until workflow completes (4317d95)
- Replace `gh pr/issue view --web` commands with clickable URLs in next-steps output (c3969c8)
- Strip `.erk/impl-context/` before restack in `erk pr sync` to avoid merge conflicts (e3720af)
- Consolidate PR validation into `--stage=impl` flag on `erk pr check` (e2bd53d)
- Convert submit pipeline to git plumbing, eliminating race conditions in shared worktrees (ea4a853)
- Increase workflow dispatch polling timeout to ~62 seconds for `erk plan submit` reliability (368a707)

### Fixed (2 new entries appended after existing)
- Fix plan-save branches incorrectly stacking on current branch instead of trunk (93df692)
- Fix `impl-signal started` to include lifecycle_stage transition, preventing stuck "planned" status (ed266b8)

### Removed (1 new entry appended after existing)
- Remove `get_plan_backend()` and `PlanBackendType`, hardcoding draft PR as the only plan backend (4ccfbb0)

## Verification
- Read updated CHANGELOG.md to confirm formatting and marker update
