# Changelog Update

## Context

Update CHANGELOG.md Unreleased section with 100 commits since last sync (36e6f5d54 → eca302f73).

## Critical File

- `CHANGELOG.md` — update "As of" marker to `eca302f73` and add entries below

## Proposed Entries

### Major Changes (2)

- Consolidate all plan management commands under `erk pr` — commands previously under `erk plan` (create, list, submit, checkout, close, view, log, replan, duplicate-check) are now at `erk pr <verb>`. The `erk plan` group has been removed. (bfb17162d)
- Remove plan ID encoding from branch names — plans are now linked to branches via `plan-ref.json` instead of embedding issue numbers in branch names (e.g., `plnd/1234-description` format is gone). (41ba25ed2)

### Added (6)

- Add persistent status bar messages for workflow operations in the TUI — async results (dispatch, address, fix-conflicts) now appear as persistent messages instead of disappearing notifications. (1026519a8)
- Add inline objective filter to `erk dash` TUI — press `o` to filter the plan list to a specific objective. (cfeef67ca)
- Add stack filter to `erk dash` TUI — filter plans by Graphite stack. (aef3007bf)
- Add `--sync` flag to `erk pr checkout` — automatically submits the checked-out PR to Graphite after checkout. (ec138061b)
- Add ObjectivePlansScreen modal to `erk dash` TUI — view all plans linked to an objective in an embedded plan table overlay. (e41d00d96)
- Add automatic tmux session persistence to `erk codespace connect` — sessions now persist in tmux without requiring an explicit flag. (9b5adb89f)

### Changed (9)

- Fix-conflicts workflow in plan detail screen now uses toast+async pattern instead of a blocking modal with live subprocess output. (eca302f73)
- Change TUI Dispatch/Queue keyboard shortcut from `s` to `d`. (85d47e68e)
- Move metadata blocks to the bottom of planned PR bodies. (8058e8d90)
- Rename `erk pr sync-divergence` command to `erk pr reconcile-with-remote`. (a406dba12)
- `erk pr dispatch` now auto-detects the PR number from the current branch when no argument is provided. (9c6b2d13a)
- Remove "Closes #N" footer from PR bodies — plans no longer auto-close linked issues on merge via PR body footer. (07fdb7f99)
- Speed up `erk dash` Plans and Learn tabs using a REST+GraphQL two-step fetch. (292c4ba97)
- Increase log panel height in plan detail screen. (30c3eb48a)
- Rename `deps-state`/`deps` columns to `head-state`/`head` in Objectives dashboard. (84bf09365)

### Fixed (13)

- Fix modal keystroke leakage to the underlying view in TUI screens. (0d105f359)
- Error correctly when `--new-slot` is used but the branch already exists in another worktree. (9d0a451b7)
- Fix Graphite tracking divergence in `erk pr dispatch`. (2791dc698)
- Fix objective head column in dashboard (plan field missing from RoadmapNode/ObjectiveNode). (c9c1e3e9a)
- Fix learn PRs incorrectly appearing in the Planned PRs tab. (8316a58a3)
- Fix TUI dispatch command CLI path and user-facing labels after command rename. (007f2e7ef)
- Fix learn plan PRs being auto-closed when their ephemeral base branch is deleted. (df52c8d97)
- Fix `erk pr submit` producing zero output on timeout. (338d24fda)
- Fix silent plan-header metadata loss during PR submit. (334fc5013)
- Fix PR diff accuracy in `get_diff_to_branch` by switching to three-dot (`...`) git syntax. (e2ad6fe4a)
- Fix TUI plan submit command crash caused by invalid `-f` flag. (5ba908048)
- Fix plan-save always basing the new branch off trunk instead of the current branch. (5160fb1fd)
- Fix `lifecycle_stage` not being updated in all code paths of the PR submit pipeline. (f8b4b9158)

### Removed (4)

- Delete `erk pr sync` command. Use `erk pr reconcile-with-remote` for conflict resolution. (4c51cdc3a)
- Delete `-t/--tmux` explicit flag from `erk codespace connect` — tmux persistence is now automatic. (e90483add)
- Eliminate `--objective-issue` flag from plan-save commands. (8e58ddee8)
- Eliminate `--no-wait` flag from dispatch workflow commands. (a50fa13f2)

## Implementation

1. Open `CHANGELOG.md`
2. Update "As of" marker to `eca302f73`
3. Add entries under appropriate category headers in the Unreleased section (preserving existing entries)
4. Category order: Major Changes → Added → Changed → Fixed → Removed
