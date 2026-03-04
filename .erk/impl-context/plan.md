# Changelog Update Plan

## Context
Update CHANGELOG.md unreleased section with commits since 9006754f2 (current HEAD: 7f57dead6).

## Changes to CHANGELOG.md

Update `<!-- As of: 9006754f2 -->` to `<!-- As of: 7f57dead6 -->`.

Add a `### Major Changes` section at the top of Unreleased (before Changed), and add new entries under existing sections:

### Major Changes (new section)
- Support stacked branches on the same worktree: implement plans on the current branch without creating a new worktree, with restructured exit-plan-mode menu and hierarchical next-steps output. Includes fixes for stale parent branch tracking, slot reuse, and branch tracking after plan-save. (473b9a769, 9ca2e1ecf, 3a969663d, 51ed4fbcc, a8347ca3f, e69b3657f, 1872695a7)

### Added (new section, before Changed)
- Support creating objectives without a roadmap: `erk objective create` and `erk objective check` now work for standalone objectives not tied to any roadmap. (7577959c5)

### Changed (append to existing)
- Always run `uv sync` during worktree activation regardless of VIRTUAL_ENV state (ccf0aeb21)

### Fixed (append to existing)
- Fix `erk up/down` navigation when worktree has a different branch checked out (51d2e25f3)
- Fix slot reuse incorrectly treating untracked files as dirty (7bd67b60a)

### Removed (new section, after Fixed)
- Delete erkbot package (dd35477c1)

## Verification
- Read the updated CHANGELOG.md to confirm formatting and entry placement
