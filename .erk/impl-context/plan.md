# Plan: Add pyproject.toml force-include sync test for bundled skills

## Context

You asked to make bundled skill management more foolproof with explicit include/exclude lists and a test catching untracked skills.

**Good news: most of this already exists.** The file `tests/unit/artifacts/test_codex_compatibility.py` already has:

- `codex_portable_skills()` — the **include list** (skills bundled for distribution)
- `claude_only_skills()` — the **exclude list** (project-only, not distributed)
- `test_codex_portable_and_claude_only_cover_all_skills()` — catches any on-disk skill that isn't in either list, and also catches duplicates (skill in both lists)
- `test_portable_skills_match_bundled()` / `test_claude_only_skills_exist()` — catches stale entries that don't have on-disk directories

**The one gap:** no test verifies that `pyproject.toml` `force-include` entries stay in sync with `codex_portable_skills()`. If someone adds a skill to the include list but forgets the `pyproject.toml` entry, the wheel won't contain the skill.

## Changes

### `tests/unit/artifacts/test_codex_compatibility.py`

Add one helper and one test:

1. **`_get_force_included_skill_names()`** — parse `pyproject.toml`, extract skill names from `[tool.hatch.build.targets.wheel.force-include]` entries matching `.claude/skills/*`

2. **`test_codex_portable_skills_match_force_include()`** — assert the set of force-included skills equals `codex_portable_skills()` exactly, with actionable error messages for missing/extra entries

Also extract a `_get_repo_root()` helper from the existing `_get_claude_skills_dir()` to share with the new helper (avoids duplicating the path resolution).

## Verification

Run: `uv run pytest tests/unit/artifacts/test_codex_compatibility.py -v`
