# erk-statusline

Custom status line for Claude Code with robbyrussell theme style.

![Screenshot](screenshots/statusline.png)

## Status Line Components

The status line displays (left to right):

- **Git repo**: `(git:repo-name)` - Current GitHub repository name
- **Worktree**: `({wt, br}:name)` or `(wt:name)` - Git worktree info ("root" for main worktree, or worktree name for linked worktrees)
- **Branch**: `(br:branch-name)` - Current git branch (combined with worktree if names match)
- **Current directory**: `(cwd:path)` - Relative path from git root (only shown if not at root)
- **Plan progress**: `(.impl X/Y)` - Implementation plan progress from `.impl/progress.md`
- **Dirty indicator**: `✗` - Shows when there are uncommitted changes
- **GitHub PR info**: `(gh:#123 plan:#456 st:XX chks:XX)`:
  - `#123` - PR number
  - `plan:#456` - Associated issue number from `.impl/issue.json`
  - `st:` - PR state emoji: `👀` published, `🚧` draft, `🎉` merged, `⛔` closed, `💥` conflicts
  - `chks:` - CI checks status: `✅` passing, `🚫` failing, `🔄` pending
- **Model**: `(S)` Sonnet, `(O)` Opus, or model initial

## Installation

```bash
uv tool install git+https://github.com/dagster-io/erk-statusline
```

Or for development:

```bash
git clone https://github.com/dagster-io/erk-statusline
cd erk-statusline
uv sync
```

## Usage

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "erk-statusline"
  }
}
```

## Development

```bash
# Run all checks (lint, typecheck, tests)
make check

# Run individual checks
make lint
make typecheck
make test

# Run tests with coverage
make test-coverage
```
