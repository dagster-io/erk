# erk-sh-bootstrap

Thin bootstrap CLI that delegates to project-local erk installations.

## How it's used

Shell integration (set up by `erk init --shell`) automatically uses this package via `uvx`:

- Users don't need to install erk-sh-bootstrap manually
- `uvx erk-sh-bootstrap` is called by the shell wrapper function
- It finds your project's `.venv/bin/erk` and delegates commands

## Manual installation (optional)

For users who prefer a persistent global command:

```bash
uv tool install erk-sh-bootstrap
```

## How it works

When you run `erk` commands, this bootstrap:

1. Looks for `.venv/bin/erk` or `venv/bin/erk` walking up from current directory
2. If found, delegates the command to the project-local erk
3. If not found, shows a helpful error message

## Override

Set `ERK_VENV` environment variable to point to a specific venv:

```bash
ERK_VENV=/path/to/my/venv erk wt list
```

## Per-project installation

In each project where you want to use erk:

```bash
uv add erk
uv sync
```
