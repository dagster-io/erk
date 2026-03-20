# Plan: Update CHANGELOG.md Unreleased Section

## Context

CHANGELOG.md unreleased section is synced as of `d5c0167db`. There are 7 new user-facing entries to add from commits merged since then. HEAD is `4637c3bfa`.

## Changes to CHANGELOG.md

1. **Update "As of" marker** on line 10: `d5c0167db` → `4637c3bfa`

2. **Append to `### Added`** (after line 23):
   - `- Wire per-user GitHub OAuth token into erk-mcp for authenticated multi-user deployments (3735d324e)`

3. **Append to `### Changed`** (after line 33):
   - `- Make `erk pr teleport` slot-aware, updating slot assignment when teleporting within a slot-assigned worktree (5b7386776)`
   - `- Switch remote dispatch workflows to Sonnet 4.6 (211f5a0bc)`

4. **Append to `### Fixed`** (after line 40):
   - `- Fix statusline model indicator to correctly display Opus/Sonnet/Haiku with 1M context suffix (3155e0417)`
   - `- Fix `get_ahead_behind` to compare named branch instead of HEAD, preventing incorrect ahead/behind counts (cc568acbe)`
   - `- Fix TUI land command argument mismatch causing error toasts on every land operation (1a2d56da9)`
   - `- Fix erk-mcp error suppression and harden HTTP auth configuration to fail closed (133e7b398)`

No new categories needed. No entries removed. Existing entries preserved as-is.

## Verification

- Read back the Unreleased section after edits to confirm correct formatting and ordering
