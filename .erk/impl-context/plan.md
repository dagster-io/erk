# Changelog Update Plan

## Context
Update CHANGELOG.md Unreleased section with 55 commits since 0.8.1 (9b42ce76d → 104f87771).

## Changes to CHANGELOG.md

Add "As of" marker and entries to the `## [Unreleased]` section:

```markdown
<!-- As of 104f87771 -->

### Major Changes

- Remove plan review PR feature — sunsets the ephemeral plan review PR workflow (259820f)
- Switch default plan backend to draft PR — `draft_pr` is now the default instead of `github` (a7692b4)

### Added

- Add `erk admin claude-ci` command for managing Claude CI workflows (1af6826)
- Add "implement locally" copyable command to TUI command palette (152c360)
- Add copyable variants for close_plan, fix_conflicts_remote, and address_remote in TUI command palette (3cf08a1)
- Add `copy_land` command to TUI command palette (9338f36)
- Add `--plan-only` flag to `erk one-shot` for generating plans without implementation (23575c8)
- Add `-d` short flag for `--delete-current` option in `erk up`/`erk down` commands (1fb2d1e)

### Changed

- Eliminate `.worker-impl/` directory, consolidating onto `.erk/impl-context/` (223542b)
- Redesign `erk plan list` to match dashboard layout (a0b042d)
- Replace `erk pr submit --skip-description` with composable `erk exec push-and-create-pr` (4c5e7ef)
- Change `erk land` default to direct execution without navigation (b5b0837)
- Collapse "impling" and "impld" stage labels to "impl" in plan lifecycle display (a2a1d28)
- Redesign objectives TUI with sparkline progress indicators (7207a79)
- Move plan-header metadata block to bottom of PR descriptions (0c3e672)
- Wrap review comment details in collapsible blocks (bf5c49e)

### Fixed

- Fix `erk land` crash when branch is checked out in another worktree (d7bc5ac)
- Fix plan-save to include branch_name in skipped_duplicate response (659563d)
- Fix branch checkout in stack-in-place path (705bac8)
- Fix WARNING comment accumulation on metadata block updates (60c75f5)
- Clear error when trigger_workflow finds skipped/cancelled run (2a49eb3)

### Removed

- Remove GitHub repository variables feature and related infrastructure (a4ba14e)
- Remove run_url gate from land PR command (9fc1dab)
```

## Verification
- Read the updated CHANGELOG.md to confirm formatting and entry order
