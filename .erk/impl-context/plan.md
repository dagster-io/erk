# Fix CI Lint Errors

## Context
`make all-ci` fails with E402 (imports not at top) and E501 (line too long) in two erkbot files, plus format check failures and stale exec reference docs.

## Changes

### 1. `packages/erkbot/src/erkbot/agent/stream.py`
- **E402**: Move `logger = logging.getLogger(__name__)` after all imports (after line 24)
- **E501 line 67**: Break long `logger.info("Tool ended: ...")` call

### 2. `packages/erkbot/src/erkbot/slack_handlers.py`
- **E402**: Move `logger = logging.getLogger(__name__)` after all imports (after the `TYPE_CHECKING` block, before `SUPPORTED_COMMANDS_TEXT`)
- **E501 line 101**: Break long `logger.debug("slack_update: ...")` call
- **E501 line 221**: Break long `logger.info("reply: ...plan-list...")` call
- **E501 line 267**: Break long `logger.warning("reply: ...one-shot...")` call

### 3. Run `ruff format` on both files to fix formatting

### 4. Regenerate exec reference docs
- Run `erk-dev gen-exec-reference-docs`

## Verification
- Run `make all-ci` to confirm all checks pass
