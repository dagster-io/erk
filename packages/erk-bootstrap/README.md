# erk-bootstrap

Thin bootstrap CLI that delegates to project-local erk installations.

## Installation

```bash
uv tool install erk-bootstrap
```

## How it works

When you run `erk` commands, this bootstrap:

1. Looks for `.venv/bin/erk` or `venv/bin/erk` walking up from your current directory
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
