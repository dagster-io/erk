# Plan: Always run `uv sync` in worktree activation scripts

## Context

When running `source "$(erk br co --new-slot --for-plan 8617 --script)" && erk implement --dangerous`, the worktree's `.venv` already exists (created when the slot was first provisioned) but is **stale** — the lockfile has since added `anthropic` as a dependency. The activation script skips `uv sync` because `.venv` exists, and only runs `uv pip install --no-deps` which doesn't install new external dependencies. This causes `ModuleNotFoundError: No module named 'anthropic'` in two places:

1. `eval "$(erk completion bash/zsh)"` within the activation script itself
2. `erk implement` after the activation script completes

## Change

**File: `src/erk/cli/activation.py` — `render_activation_script()` (lines 198-212)**

Current logic:
```bash
if [ ! -d {venv_dir} ]; then
    echo 'Creating virtual environment with uv sync...'
    uv sync
fi
uv pip install --no-deps --quiet -e . -e packages/erk-shared -e packages/erk-statusline
```

New logic:
```bash
if [ ! -d {venv_dir} ]; then
    __erk_log "->" "Creating virtual environment..."
fi
uv sync --quiet
uv pip install --no-deps --quiet -e . -e packages/erk-shared -e packages/erk-statusline
```

`uv sync` always runs — it's fast on warm venvs (~200ms) and ensures new external dependencies get installed. The `uv pip install --no-deps` line is kept as a fast editable-package refresh (per tripwire in `workspace-activation.md`).

**File: `docs/learned/erk/workspace-activation.md`**

Update step 3 from "Create venv if it doesn't exist (`uv sync`)" to "Sync dependencies (`uv sync --quiet`) — creates venv if missing, installs new deps if lockfile changed".

## Verification

1. Run `make fast-ci` (unit tests + lint)
2. Manual: confirm that `source .erk/bin/activate.sh` in a worktree with a stale venv correctly installs new deps
