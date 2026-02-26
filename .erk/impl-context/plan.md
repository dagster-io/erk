# Hoist Slug LLM Call Out of `erk one-shot` CLI

## Context

The `/erk:one-shot` skill runs `erk one-shot --file <path>` as a Bash command from within a Claude Code session. The CLI internally spawns `claude --print` (subprocess) to generate a branch slug via Haiku. This nested Claude subprocess hangs inside an active Claude Code session.

Fix: add `--slug` to the CLI so the skill can generate the slug inline (Claude is already the LLM) and pass it, making the CLI purely mechanical.

## Changes

### 1. `src/erk/cli/commands/one_shot_dispatch.py`

- Add `slug: str | None` field to `OneShotDispatchParams`
- In `dispatch_one_shot()` (~line 184-191): LBYL check — if `params.slug is not None`, use it directly and skip the LLM call; otherwise keep existing `generate_slug_or_fallback()` path
- Update `generate_branch_name()` signature: add `slug: str | None` param with same LBYL pattern (used in dry-run path, line 144)

### 2. `src/erk/cli/commands/one_shot.py`

- Add `--slug` Click option (type=str, default=None)
- Pass `slug` through to `OneShotDispatchParams`

### 3. `src/erk/cli/commands/objective/plan_cmd.py`

- Pass `slug=None` at both `OneShotDispatchParams` construction sites (lines ~251 and ~708)
- These retain existing LLM slug generation (they run from a normal terminal, not nested in Claude Code)

### 4. `.claude/commands/erk/one-shot.md`

- Add step 2: generate a 2-4 word slug inline (rules match `BRANCH_SLUG_SYSTEM_PROMPT`)
- Update step 4: pass `--slug <generated-slug>` to the CLI invocation

### 5. Tests

- `tests/commands/one_shot/test_one_shot_dispatch.py`: Add `slug=None` to all 3 `OneShotDispatchParams` construction sites (lines 35, 104, 210)
- `tests/commands/one_shot/test_branch_name.py`: Add `slug=None` to all 3 `generate_branch_name` calls (lines 11, 23, 36)
- Add one new test verifying the pre-generated slug path skips the LLM call

## Verification

```
uv run pytest tests/commands/one_shot/ -x
```
