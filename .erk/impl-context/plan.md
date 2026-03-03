# Update CHANGELOG.md Unreleased Section

## Context

Syncing the Unreleased section of CHANGELOG.md with commits merged to master since `41d6099a3`. Three entries were filtered per user direction (MCP server — in development; perpetual objectives — filtered; erkbot removal — filtered).

## Changes to Make

### 1. Update "As of" marker
Change the `As of` line to `9006754f2`.

### 2. Add entries under "Changed" header

```markdown
- Show progress feedback during PR description generation: `erk pr submit` and `erk pr rewrite` now display "Still waiting..." messages at 3-second intervals while Claude generates the PR description, replacing silence during long API call windows. (9006754f2)
- Auto-activate worktree environment on stack-in-place checkout: When using `erk br co` from an assigned slot, the activation script now runs automatically instead of printing copy-paste instructions. (b9f51ab61)
- Improve branch checkout messaging for plan flows: The message when checking out a plan branch changes from "Using existing branch" to "Checking out plan branch". (081094be4)
```

### 3. Add entries under "Fixed" header

```markdown
- Fix `erk down -f -d` from root worktree with non-trunk branch: Navigation to trunk from the root worktree no longer fails with "Cannot create worktree for trunk branch" when a non-trunk branch is checked out. (d7a070a62)
- Fix `erk pr dispatch` when no impl-context reference exists: Dispatch auto-detection now falls back to resolving the plan number from the current branch via the GitHub API. (a0e1ed2ff)
- Fix dispatch metadata write for plans missing a plan-header: A minimal plan-header is now created automatically before writing dispatch metadata, preventing a silent failure. (119dc9026)
- Fix impl-context files leaking into implementation PRs: Removes an incorrect optimization that preserved impl-context for plan branches during submit pipeline cleanup. (ac59a65fb)
```

## File to Modify

- `CHANGELOG.md` — Unreleased section only

## Verification

After editing, confirm:
1. "As of" marker reads `9006754f2`
2. 7 new entries present (3 Changed, 4 Fixed)
3. Existing entries are untouched
