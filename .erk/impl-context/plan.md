# Delete erkbot package

## Context

The `erkbot` package (a Slack bot integration for erk) is being removed from the codebase. No other packages depend on erkbot — it only consumes `erk` and `erk-shared`. The deletion is clean and self-contained.

## Steps

### 1. Delete the erkbot package directory

```
rm -rf packages/erkbot/
```

This removes all source code (~23 files), tests (~23 files), Makefile, pyproject.toml, README.md, SETUP.md.

### 2. Delete erkbot documentation

Delete these files/directories:
- `docs/learned/integrations/erkbot/` (agent-event-system.md, erkbot-architecture.md)
- `docs/learned/integrations/erkbot-agent-config.md`
- `docs/learned/integrations/slack-bot-patterns.md`
- `docs/learned/testing/bolt-async-dispatch-testing.md`

### 3. Remove erkbot references from `Makefile`

- Remove `test-erkbot` from `.PHONY` line
- Delete `test-erkbot:` target (lines 28-29)
- Remove `slackbot` from `.PHONY` line
- Delete `slackbot:` target (lines 170-171)
- Remove erkbot test lines from `py-fast-ci`, `fast-ci`, and `all-ci` targets (lines 92, 108, 126)

### 4. Remove erkbot references from `.github/workflows/ci.yml`

- Delete `erkbot-tests` job (lines 164-173)
- Remove `erkbot-tests` from `ci-summarize` needs list (line 448)
- Remove `erkbot-tests` failure condition from ci-summarize `if` (line 463)

### 5. Run `uv lock` to regenerate lockfile

The lockfile will drop erkbot and its unique dependencies (slack-bolt, slack-sdk, claude-agent-sdk, etc.).

### 6. Run `erk docs sync` to regenerate auto-generated index/tripwire files

This will update:
- `docs/learned/integrations/index.md` (auto-generated, will drop erkbot entries)
- `docs/learned/integrations/tripwires.md` (auto-generated, will drop erkbot tripwires)
- `docs/learned/index.md` (if affected)

## Verification

1. `uv sync` succeeds
2. `make py-fast-ci` passes (lint, format, ty, unit tests)
3. Grep for "erkbot" across codebase confirms no stale references
