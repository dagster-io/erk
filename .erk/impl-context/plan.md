# Rename Skills: Add `refac-` Prefix

## Context

Two skills (`cli-push-down`, `module-to-subpackage`) are being given a `refac-` prefix to establish a naming convention for refactoring-category skills.

## Changes

### 1. Rename skill directories (git mv)
- `.claude/skills/cli-push-down/` → `.claude/skills/refac-cli-push-down/`
- `.claude/skills/module-to-subpackage/` → `.claude/skills/refac-module-to-subpackage/`

### 2. `src/erk/capabilities/skills/bundled.py`
- `"module-to-subpackage"` → `"refac-module-to-subpackage"` (line 24)
- `"cli-push-down"` key → `"refac-cli-push-down"` (line 47)

### 3. `src/erk/core/capabilities/codex_portable.py`
- `"cli-push-down"` → `"refac-cli-push-down"` (line 18)

### 4. `pyproject.toml`
- `".claude/skills/cli-push-down" = "erk/data/claude/skills/cli-push-down"` → update both sides to `refac-cli-push-down` (line 67)
  - Also rename the actual data directory if it exists separately

### 5. `docs/developer/agentic-engineering-patterns/README.md`
- Update `cli-push-down` reference in skill load instruction (line 49)

### 6. SKILL.md files (no changes needed)
The `SKILL.md` files inside each skill directory don't need updating — the skill name isn't typically hardcoded inside the file itself (verify on read).

## Files to Modify
- `src/erk/capabilities/skills/bundled.py`
- `src/erk/core/capabilities/codex_portable.py`
- `pyproject.toml`
- `docs/developer/agentic-engineering-patterns/README.md`

## Directories to Rename (git mv)
- `.claude/skills/cli-push-down/` → `.claude/skills/refac-cli-push-down/`
- `.claude/skills/module-to-subpackage/` → `.claude/skills/refac-module-to-subpackage/`
- Also check if `src/erk/data/claude/skills/cli-push-down/` exists (pyproject.toml data path) and rename if so

## Verification
- Run `erk skill list` or equivalent to confirm skills appear under new names
- Check `erk capabilities` or `erk dash` to confirm no broken references
- Run `make fast-ci` to catch any test failures from the rename
