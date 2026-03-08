---
title: Workspace Activation and Package Refresh
read_when:
  - "modifying worktree activation scripts"
  - "debugging stale package versions in worktrees"
  - "understanding how workspace packages are refreshed"
  - "changing activation script generation"
tripwires:
  - action: "removing uv sync --quiet from activation"
    warning: "uv sync --quiet refreshes workspace packages on every activation. Without it, worktrees may use stale versions of erk, erk-shared, or erk-statusline after switching branches."
---

# Workspace Activation and Package Refresh

Every erk worktree runs an activation script on entry. The script refreshes workspace packages to ensure the worktree uses the current branch's code, not stale cached versions.

## Package Refresh

<!-- Source: src/erk/cli/activation.py, render_activation_script -->

The activation script runs `uv sync --quiet` on every worktree activation. This synchronizes all workspace packages (`erk`, `erk-shared`, `erk-statusline`) with the current branch's code, handling both editable installs and external dependencies in a single operation.

### Why On Every Activation

When switching between worktrees or branches, the editable install paths may point to different code. Without refresh:

- A worktree created from an older branch may have stale `erk-shared` APIs
- Switching branches within a worktree wouldn't pick up new package entry points
- New CLI commands added in one branch wouldn't be available after checkout

The per-activation refresh ensures the installed packages always match the current checkout.

## Activation Script Structure

For the full activation script structure, VIRTUAL_ENV guard behavior, and `force_script_activation` parameter, see [Activation Scripts](../cli/activation-scripts.md).

## Related Documentation
