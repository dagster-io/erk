# Plan: Rename erk-slack-bot to erkbot

## Context

The `packages/erk-slack-bot` package is being renamed to `erkbot` for brevity. This is a pure rename — no functional changes.

## Naming Mapping

| Old | New |
|-----|-----|
| `erk-slack-bot` (package/CLI name) | `erkbot` |
| `erk_slack_bot` (Python module) | `erkbot` |
| `packages/erk-slack-bot/` (directory) | `packages/erkbot/` |

## Steps

### 1. Directory renames (git mv)

```
git mv packages/erk-slack-bot packages/erkbot
mv packages/erkbot/src/erk_slack_bot packages/erkbot/src/erkbot
```

(Inner `src/` rename uses plain `mv` since git tracks content, not directories.)

### 2. Update `packages/erkbot/pyproject.toml`

- `name = "erk-slack-bot"` → `name = "erkbot"`
- `erk-slack-bot = "erk_slack_bot.cli:main"` → `erkbot = "erkbot.cli:main"`

### 3. Bulk replace `erk_slack_bot` → `erkbot` in all `.py` files

Source files (7 files with imports):
- `src/erkbot/__init__.py` — docstring
- `src/erkbot/app.py` — 2 imports
- `src/erkbot/cli.py` — 2 imports
- `src/erkbot/parser.py` — 1 import
- `src/erkbot/runner.py` — 1 import
- `src/erkbot/slack_handlers.py` — 5 imports
- `src/erkbot/utils.py` — 1 import + resource package string
- `src/erkbot/agent/stream.py` — 1 import
- `src/erkbot/agent/helpers.py` — 1 import

Test files (10 files with imports + @patch strings):
- `tests/test_app.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_parser.py`
- `tests/test_runner.py`
- `tests/test_slack_handlers.py`
- `tests/test_utils.py`
- `tests/test_agent_events.py`
- `tests/test_agent_helpers.py`
- `tests/test_agent_stream.py`

### 4. Update Makefiles

- `packages/erkbot/Makefile`: `erk-slack-bot` → `erkbot` (2 occurrences)
- Root `Makefile` line 186: `cd packages/erk-slack-bot` → `cd packages/erkbot`

### 5. Update `packages/erkbot/README.md`

- Header text if it mentions "Erk Slack Bot"

### 6. Update `.impl/plan.md`

- All path references `packages/erk-slack-bot/` → `packages/erkbot/`
- All import references `erk_slack_bot` → `erkbot`

### 7. Reinstall package

```
uv sync
```

No root `pyproject.toml` change needed — workspace uses `members = ["packages/*"]` glob.

## Verification

1. `uv sync` succeeds
2. `cd packages/erkbot && make -n dev` — verify Makefile references are correct
3. Run package tests: `cd packages/erkbot && uv run pytest tests/`
4. `uv run erkbot --help` — confirm CLI entry point works
