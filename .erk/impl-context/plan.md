# CHANGELOG.md Update

## Context

Syncing the Unreleased section of CHANGELOG.md with 8 new user-facing commits merged to master since the last sync marker (`623898bca`).

## File

`CHANGELOG.md`

## Changes

### 1. Update "As of" marker (line 10)

```
<!-- As of: 623898bca -->
```
→
```
<!-- As of: b372dfbcc -->
```

### 2. Append to existing `### Added` section (after line 17)

```markdown
- Add `dispatch_ref` config to override workflow dispatch branch for testing workflow changes on feature branches (064737c47)
- Add `launch one-shot` command for triggering one-shot workflows with `--prompt`/`-f` options (e86efb1e4)
- Display learn plan PR link in `erk land` output (90bfd7870)
- Add session preprocessing stats to `erk land` discovery output (2ed31d082)
```

### 3. Append to existing `### Changed` section (after line 23)

```markdown
- Rebase slot worktree placeholder branch onto master after `erk land` to keep slots fresh (92f5f2e7f)
```

### 4. Append to existing `### Fixed` section (after line 29)

```markdown
- Fix CI check counts where skipped checks were counted as passing — planned PRs now show "0/0" instead of "13/13" (02cd44a1f)
- Fix stacked plan branch checkout by rebasing onto parent before `gt track` (6b0978292)
- Consolidate all plan creation paths to use draft PR workflow, completing migration away from issue-based plans (c638d7272)
```

## Verification

Read CHANGELOG.md after edits to confirm:
- Marker updated to `b372dfbcc`
- 4 Added, 1 Changed, 3 Fixed entries appended below existing entries
- Existing entries unchanged
