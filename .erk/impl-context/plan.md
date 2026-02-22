# Add `--env` flag to `erk codespace connect`

## Context

`ERK_PLAN_BACKEND=draft_pr` needs to be set in codespace sessions, but `erk codespace connect` has no mechanism to inject environment variables into the remote bootstrap command. This adds a `--env` CLI option to pass arbitrary env vars.

## Changes

### 1. Add `--env` option to connect command

**File:** `src/erk/cli/commands/codespace/connect_cmd.py`

- Add `@click.option("--env", "env_vars", multiple=True, help="Set env var (KEY=VALUE)")`
- Parse each `--env` value into key=value pairs, error on invalid format
- For non-shell mode: prepend `export KEY=VALUE &&` to the remote command (before `git pull`)
- For `--shell` mode: wrap in `bash -l -c 'export KEY=VALUE && exec bash -l'` so the env vars are available in the interactive shell
- Use `shlex.quote` on values to prevent shell injection

### 2. Add tests

**File:** `tests/unit/cli/commands/codespace/test_connect_cmd.py`

- `test_connect_with_env_injects_export`: Pass `--env ERK_PLAN_BACKEND=draft_pr`, assert remote command contains `export ERK_PLAN_BACKEND=draft_pr`
- `test_connect_with_multiple_env_vars`: Pass two `--env` flags, assert both exports present
- `test_connect_env_with_shell_flag`: Pass `--env` with `--shell`, assert env vars injected into shell command
- `test_connect_env_invalid_format_errors`: Pass `--env INVALID` (no `=`), assert error message

## Verification

```bash
uv run pytest tests/unit/cli/commands/codespace/test_connect_cmd.py
```
