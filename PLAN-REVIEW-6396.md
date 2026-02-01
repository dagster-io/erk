# Plan: `erk codespace run objective next-plan ISSUE_REF`

## Overview

Add `erk codespace run` subgroup that executes erk commands remotely on a codespace. First supported command: `objective next-plan`. Fire-and-forget execution with auto-start of stopped codespaces.

## Design Decision: Invoke erk CLI remotely (not raw claude)

Instead of constructing a `claude --dangerously-skip-permissions ...` command string locally and sending it over SSH, the remote side invokes `erk objective next-plan` directly. Benefits:

- **Single source of truth** — slash command format, permission mode, and claude args stay in `next_plan_cmd.py`
- **No string construction** — avoids fragile quoting/escaping of shell commands
- **Testable** — no need to assert on string contents; test behavior through fakes
- **Extensible** — adding a new remoteable command is just `erk <whatever>` on the remote

The setup steps (`git pull && uv sync && source .venv/bin/activate`) are still a shell string since they bootstrap the environment before erk is available. This is extracted into a shared helper.

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

### 3. Create codespace run helper

**Create** `src/erk/core/codespace_run.py`

Function `build_codespace_run_command(erk_command: str) -> str` that wraps any erk CLI command in the setup + nohup pattern:

```python
def build_codespace_run_command(erk_command: str) -> str:
    """Wrap an erk CLI command for fire-and-forget codespace execution."""
    setup = "git pull && uv sync && source .venv/bin/activate"
    return f"bash -l -c '{setup} && nohup {erk_command} > /tmp/erk-run.log 2>&1 &'"
```

This is the only place that knows about the setup/nohup pattern. Every remoteable command calls it with its own erk CLI string.

### 4. Create `run` group and `objective next-plan` command

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
    remote_cmd = build_codespace_run_command(f"erk objective next-plan {issue_ref}")
    exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
    # report success/failure
```

The `ISSUE_REF` argument is the only duplicated Click decorator between local and remote commands. This is acceptable — it's one line, and the actual logic (what slash command to run, what permission mode) stays in `next_plan_cmd.py`.

### 5. Register `run` group

**Modify** `src/erk/cli/commands/codespace/__init__.py` — add `codespace_group.add_command(run_group)`

### 6. Tests

- `tests/cli/commands/codespace/test_resolve.py` — resolution helper (name, default, errors)
- `tests/cli/commands/codespace/run/objective/test_next_plan_cmd.py` — remote command using FakeCodespace/FakeCodespaceRegistry
- `tests/core/test_codespace_run.py` — `build_codespace_run_command` output

## Extensibility

Adding a new remoteable command (e.g., `erk codespace run plan replan`) requires:
1. Create group/command under `codespace/run/`
2. Call `build_codespace_run_command("erk plan replan ...")` with the appropriate CLI string
3. Register in `run/__init__.py`

No shared slash command builders needed — the remote side just invokes the erk CLI.

## Key Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/codespace/resolve.py` | Create |
| `src/erk/core/codespace_run.py` | Create |
| `src/erk/cli/commands/codespace/run/__init__.py` | Create |
| `src/erk/cli/commands/codespace/run/objective/__init__.py` | Create |
| `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py` | Create |
| `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` | Modify |
| `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` | Modify |
| `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` | Modify |
| `src/erk/cli/commands/codespace/__init__.py` | Modify |
| `src/erk/cli/commands/codespace/connect_cmd.py` | Modify |

## Verification

1. `erk codespace run objective next-plan --help` shows correct args/options
2. Tab completion works for `erk codespace run <TAB>` → `objective`, and `erk codespace run objective <TAB>` → `next-plan`
3. Unit tests pass for resolution, command building, and the full command
4. `make fast-ci` passes
