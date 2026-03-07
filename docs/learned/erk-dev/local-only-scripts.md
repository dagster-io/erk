---
title: Local-Only Scripts Belong in erk-dev
read_when:
  - "adding a new exec script"
  - "creating a command only used by local slash commands"
  - "deciding whether a script belongs in erk or erk-dev"
  - "moving scripts between erk and erk-dev"
tripwires:
  - action: "adding an exec script that is only called by local slash commands"
    warning: "Local-only scripts should live in erk-dev, not erk. The erk package ships to users; erk-dev is developer tooling."
---

# Local-Only Scripts Belong in erk-dev

## Principle

Scripts that are **only invoked by local slash commands** (`.claude/commands/local/`) should live in the `erk-dev` package, not in the main `erk` package.

**Why:** The `erk` package ships to users. Code that only supports local developer workflows shouldn't be bundled in the shipped package.

## Decision Framework

| Invoked by | Package | Example |
|---|---|---|
| CI workflows, hooks, remote dispatch | `erk` (exec scripts) | `plan-save`, `impl-init`, `pre-tool-use-hook` |
| Local slash commands only | `erk-dev` | `audit-collect` |
| Developer tooling (release, lint, etc.) | `erk-dev` | `bump-version`, `clean-cache` |

## How to Implement in erk-dev

1. Create command directory: `packages/erk-dev/src/erk_dev/commands/<name>/`
2. Add `__init__.py` and `command.py`
3. Name the function `<name>_command` (e.g., `audit_collect_command`)
4. Use `ErkDevContext` for dependency injection (`git`, `github`, `repo_root`)
5. Register in `packages/erk-dev/src/erk_dev/cli/__init__.py`
6. Update the slash command to call `erk-dev <name>` instead of `erk exec <name>`

## Testing

erk-dev commands use `ErkDevContext` for fakes injection:

```python
from erk_dev.cli import cli
from erk_dev.context import ErkDevContext

ctx = ErkDevContext(git=fake_git, github=fake_github, repo_root=tmp_path)
result = runner.invoke(cli, ["my-command"], obj=ctx)
```

See [testing.md](testing.md) for full patterns.
