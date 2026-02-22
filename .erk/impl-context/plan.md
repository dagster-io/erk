# Changelog Update Plan

## Context
Routine changelog sync — 15 commits merged to master since last sync (491610bc4). User reviewed the proposal and approved with one adjustment: no Major Changes category (move branch naming slugs to Added).

## Changes to CHANGELOG.md

Add an "As of" marker and new entries to the `## [Unreleased]` section (currently empty, between lines 8-10):

### Added (3)
- LLM-generated branch name slugs with shortened `plnd/` prefix for meaningful, compact branch names (fcb6890ec, 19aa595e0)
- Add `--env` flag to `erk codespace connect` for setting environment variables in remote sessions (8e5c5370f)
- Add `-f/--force` flag to `erk up`/`erk down` to skip interactive prompts and auto-close PRs during destructive operations (a70c3e7d8)

### Changed (2)
- Restore abbreviated stage names (impling, impld) in TUI dashboard to fit column width (177a1838f)
- Enhance objective view with parallel in-flight status, planning indicator, and multiple unblocked nodes (a05e6a5a6)

### Fixed (1)
- Fix objective prose reconciliation reading metadata-only body instead of comment's objective-body block (0d54e2532)

## Verification
- Read the updated Unreleased section to confirm formatting and ordering
