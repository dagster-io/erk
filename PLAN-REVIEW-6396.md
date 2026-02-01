# Plan: `erk codespace run objective next-plan ISSUE_REF`

## Overview

Add `erk codespace run` subgroup that executes erk commands remotely on a codespace. First supported command: `objective next-plan`. Fire-and-forget execution with auto-start of stopped codespaces.

## CLI Invocation

```bash
erk codespace run objective next-plan 42
erk codespace run objective next-plan 42 -c my-codespace
```

- `ISSUE_REF` — positional argument (same as `erk objective next-plan`)
- `-c`/`--codespace` — optional, defaults to default codespace (same resolution as `erk codespace connect`)

## Implementation Steps

### 1. Extract codespace resolution helper

**Create** `src/erk/cli/commands/codespace/resolve.py`

Extract the name-or-default resolution logic from `connect_cmd.py` (lines 26-41) into a `resolve_codespace(registry, name) -> RegisteredCodespace` function. Both `connect_cmd` and the new `run` commands will use it.

**Modify** `src/erk/cli/commands/codespace/connect_cmd.py` — replace inline resolution with call to `resolve_codespace`.

### 2. Add `start_codespace` to Codespace gateway

**Modify** `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` — add abstract method:
```python
def start_codespace(self, gh_name: str) -> None
```

**Modify** `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` — implement via `subprocess.run(["gh", "codespace", "start", "-c", gh_name], check=True)`

**Modify** `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` — track calls in `_started_codespaces: list[str]`, expose via property.

### 3. Extract slash command builder from `next_plan_cmd`

**Modify** `src/erk/cli/commands/objective/next_plan_cmd.py` — extract:
```python
def next_plan_slash_command(issue_ref: str) -> str:
    return f"/erk:objective-next-plan {issue_ref}"
```
Both local and remote commands import this. Single source of truth for the slash command format.

### 4. Create remote command builder

**Create** `src/erk/core/remote_command.py`

Function `build_remote_claude_command(*, slash_command: str) -> str` that constructs:
```
bash -l -c 'git pull && uv sync && source .venv/bin/activate && nohup claude --dangerously-skip-permissions --permission-mode plan "/erk:objective-next-plan 42" > /tmp/erk-run.log 2>&1 &'
```

Uses `build_claude_command_string()` from `interactive_claude.py` to construct the claude portion.

### 5. Create `run` group and `objective next-plan` command

**Create** `src/erk/cli/commands/codespace/run/__init__.py` — `run` Click group
**Create** `src/erk/cli/commands/codespace/run/objective/__init__.py` — `objective` Click group under `run`
**Create** `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py` — the command:

```python
@click.command("next-plan")
@click.argument("issue_ref")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name")
@click.pass_obj
def run_next_plan(ctx: ErkContext, issue_ref: str, name: str | None) -> None:
    codespace = resolve_codespace(ctx.codespace_registry, name)
    ctx.codespace.start_codespace(codespace.gh_name)
    slash_cmd = next_plan_slash_command(issue_ref)
    remote_cmd = build_remote_claude_command(slash_command=slash_cmd)
    exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
    # report success/failure
```

### 6. Register `run` group

**Modify** `src/erk/cli/commands/codespace/__init__.py` — add `codespace_group.add_command(run_group)`

### 7. Tests

- `tests/cli/commands/codespace/test_resolve.py` — resolution helper (name, default, errors)
- `tests/cli/commands/codespace/run/objective/test_next_plan_cmd.py` — remote command using FakeCodespace/FakeCodespaceRegistry
- `tests/core/test_remote_command.py` — remote command string construction

## Extensibility

Adding a new remoteable command (e.g., `erk codespace run plan replan`) requires:
1. Create group/command under `codespace/run/`
2. Extract a slash command builder from the local command
3. Register in `run/__init__.py`

All shared infrastructure (resolve, start, remote command builder) is reused.

## Key Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/codespace/resolve.py` | Create |
| `src/erk/core/remote_command.py` | Create |
| `src/erk/cli/commands/codespace/run/__init__.py` | Create |
| `src/erk/cli/commands/codespace/run/objective/__init__.py` | Create |
| `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py` | Create |
| `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` | Modify |
| `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` | Modify |
| `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` | Modify |
| `src/erk/cli/commands/codespace/__init__.py` | Modify |
| `src/erk/cli/commands/codespace/connect_cmd.py` | Modify |
| `src/erk/cli/commands/objective/next_plan_cmd.py` | Modify |

## Verification

1. `erk codespace run objective next-plan --help` shows correct args/options
2. Tab completion works for `erk codespace run <TAB>` → `objective`, and `erk codespace run objective <TAB>` → `next-plan`
3. Unit tests pass for resolution, command building, and the full command
4. `make fast-ci` passes