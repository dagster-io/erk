# Changelog Update Plan

## Context

Syncing CHANGELOG.md unreleased section with 23 commits merged to master since marker `ebba4e54f`. User has reviewed and approved the categorization proposal.

## File to Modify

`CHANGELOG.md`

## Changes

1. **Update "As of" marker** on line 10: `ebba4e54f` → `bae59f09f`

2. **Add new "Major Changes" section** after the marker (before existing "Added"):
   - Add `--repo` flag to `erk launch` and `erk objective plan`, enabling remote workflow dispatch and planning without requiring a local git checkout (bae59f09f, c17f25a5f)

3. **Append to existing "Added" section** (after line 23, the last existing Added entry):
   - Add objective link insertion to PR body for better visibility of objective associations (c56e0626a)
   - Add progress output to `erk land` pipeline and stack commands showing real-time status (3aff883f4)
   - Add `erk launch consolidate-learn-plans` workflow for autonomous consolidation of outstanding learn plans (4eea8f29a)

4. **Append to existing "Changed" section** (after line 39, the last existing Changed entry):
   - Rename dashboard "Planned PRs" to "PRs" and apply `erk-pr` label to all erk-submitted PRs, showing plan and code PRs in unified view (63134a17f)
   - Improve `erk pr rebase` to skip tracking check when Graphite restack is in progress, preventing stuck state during conflicts (166d63639)

5. **Append to existing "Fixed" section** (after line 46, the last existing Fixed entry):
   - Fix incremental dispatch not writing workflow dispatch metadata to plan-header, causing empty run columns in dashboard (aed52e300)
   - Fix `update_local_ref` desyncing checked-out worktrees, causing phantom modifications in `git status` after dispatch operations (1724e572e)

## Verification

Read back the Unreleased section to confirm correct formatting and ordering.
