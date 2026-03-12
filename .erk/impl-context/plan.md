# Plan: Improve `erk pr teleport` help string

## Context

The current help string explains teleport vs `erk pr checkout` but doesn't convey the full value proposition — particularly what teleport does beyond `gh pr checkout`. The user wants the help text to better document teleport's capabilities.

## Changes

### File: `src/erk/cli/commands/pr/teleport_cmd.py`

Update the `pr_teleport` Click command docstring (lines 47-63) to add a "Beyond gh pr checkout" section listing:

- Force-resets local branch to match remote (discards unpushed commits)
- Worktree pool integration (navigates to existing worktrees, updates slot assignments)
- Graphite registration (tracks/retracks branch, fetches base for stacked PRs)
- Shell activation scripts (`--script` mode for cmux)
- `--sync` runs `gt submit` after teleport

Keep the existing structure (summary, checkout-vs-teleport guidance, examples) and add the new section between the guidance and examples.

## Verification

```bash
uv run python -m erk pr teleport --help
```
