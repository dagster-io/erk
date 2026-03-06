# Create module-to-subpackage skill

## Context

During a session splitting `test_capabilities.py` into submodules, a repeatable process was identified for converting monolithic Python modules into subpackages. This skill captures that process so agents can execute it reliably on any large module.

## Plan

### 1. Create skill file

Create `.claude/skills/module-to-subpackage/SKILL.md` with the content from the existing plan (`prancy-floating-moon.md`). The skill covers 7 phases: structural inventory, target discovery, grouping design, shared code placement, execution, verification, and PR workflow.

Key aspects of the skill content:
- YAML frontmatter with `name: module-to-subpackage` and description with trigger phrases
- Pure reorg discipline (no logic changes)
- Phase-based workflow from inventory through verification
- PR workflow guidance including pre-existing issue resolution pattern

### 2. Register as unbundled + claude-only (3 file touches per onboarding skill)

**`src/erk/capabilities/skills/bundled.py`** — Add `"module-to-subpackage"` to `_UNBUNDLED_SKILLS` frozenset (line ~17)

**`src/erk/core/capabilities/codex_portable.py`** — Add `"module-to-subpackage"` to `claude_only_skills()` (line ~36)

No `pyproject.toml` changes needed (unbundled skills skip force-include).

## Files to modify

| File | Change |
|------|--------|
| `.claude/skills/module-to-subpackage/SKILL.md` | Create (skill content) |
| `src/erk/capabilities/skills/bundled.py` | Add to `_UNBUNDLED_SKILLS` |
| `src/erk/core/capabilities/codex_portable.py` | Add to `claude_only_skills()` |

## Verification

- Run `make fast-ci` via devrun agent to confirm registration tests pass
- Verify skill frontmatter parses (name matches directory, description present)
