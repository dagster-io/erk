---
name: erk-skill-onboarding
description: >
  Guide for adding new skills to the erk project. Use when creating a new skill, registering
  a skill in bundled/unbundled registries, classifying codex portability, or debugging why a
  skill isn't appearing in tests or capability lists.
---

# Erk Skill Onboarding

Complete guide for adding a new skill to erk. Covers the decision tree, every file you need to touch, and which tests validate each registration.

## Decision Tree

Answer three questions to determine which files to update:

### 1. Bundled or Unbundled?

- **Bundled** = distributed to external projects via `erk init capability add <name>`
- **Unbundled** = lives in `.claude/skills/` but is only used within the erk repo itself

### 2. Codex Portable or Claude-Only?

- **Codex Portable** = works with any AI agent (no Claude-specific features like hooks, session logs, slash commands)
- **Claude-Only** = references Claude Code features (hooks, session logs, `$` skill references, slash commands)

### 3. Required or Optional? (bundled only)

- **Required** = auto-installed by `erk init` (core workflow skills)
- **Optional** = user opts in via `erk init capability add`

## Registry Files

### 1. Skill Content: `.claude/skills/<name>/SKILL.md`

Every skill needs a `SKILL.md` with valid frontmatter:

```yaml
---
name: my-skill # must match directory name, max 64 chars
description: > # max 1024 chars, used for trigger matching
  Description of when to use this skill.
---
```

The `name` field MUST exactly match the directory name under `.claude/skills/`.

### 2. Bundle Classification: `src/erk/capabilities/skills/bundled.py`

**If bundled** — add to the `bundled_skills()` dict:

```python
def bundled_skills() -> dict[str, str]:
    return {
        ...
        "my-skill": "Brief description for CLI display",
    }
```

If required, also add to `_REQUIRED_BUNDLED_SKILLS`.

**If unbundled** — add to `_UNBUNDLED_SKILLS` frozenset:

```python
_UNBUNDLED_SKILLS: frozenset[str] = frozenset(
    {
        ...
        "my-skill",
    }
)
```

### 3. Portability Classification: `src/erk/core/capabilities/codex_portable.py`

**If codex portable** — add to `codex_portable_skills()`:

```python
def codex_portable_skills() -> frozenset[str]:
    return frozenset(
        {
            ...
            "my-skill",
        }
    )
```

**If claude-only** — add to `claude_only_skills()`:

```python
def claude_only_skills() -> frozenset[str]:
    return frozenset(
        {
            ...
            "my-skill",
        }
    )
```

### 4. Wheel Packaging: `pyproject.toml` (bundled + portable only)

**Only needed for bundled skills that are codex portable.** Add a force-include entry:

```toml
[tool.hatch.build.targets.wheel.force-include]
".claude/skills/my-skill" = "erk/data/claude/skills/my-skill"
```

Unbundled skills and claude-only skills skip this step.

**Note:** Actually ALL bundled skills need force-include (not just portable ones). The force-include list should match the `bundled_skills()` dict entries.

## Test Validation Matrix

These tests in the test suite catch missing registrations:

| Test                                                   | File                                               | What It Catches                                            |
| ------------------------------------------------------ | -------------------------------------------------- | ---------------------------------------------------------- |
| `test_all_skills_have_codex_required_frontmatter`      | `tests/unit/artifacts/test_codex_compatibility.py` | Missing or invalid SKILL.md frontmatter (name/description) |
| `test_codex_portable_and_claude_only_cover_all_skills` | `tests/unit/artifacts/test_codex_compatibility.py` | Skill missing from BOTH portable and claude-only lists     |
| `test_bundled_and_unbundled_cover_all_skills`          | `tests/unit/artifacts/test_codex_compatibility.py` | Skill missing from BOTH bundled and unbundled lists        |
| `test_codex_portable_skills_match_force_include`       | `tests/unit/artifacts/test_codex_compatibility.py` | Portable skill missing from pyproject.toml force-include   |
| `test_all_codex_portable_skills_have_capability`       | `tests/unit/core/test_capabilities.py`             | Portable skill not registered as a capability              |
| `test_all_skill_capabilities_registered`               | `tests/unit/core/test_capabilities.py`             | Bundled skill not in capability registry                   |

If `make fast-ci` fails after adding a skill, check these tests first.

## Quick-Path Checklists

### New Unbundled + Claude-Only Skill (simplest: 3 file touches)

1. Create `.claude/skills/<name>/SKILL.md` with frontmatter
2. Add `"<name>"` to `_UNBUNDLED_SKILLS` in `src/erk/capabilities/skills/bundled.py`
3. Add `"<name>"` to `claude_only_skills()` in `src/erk/core/capabilities/codex_portable.py`

### New Bundled + Portable + Optional Skill (full: 4 file touches)

1. Create `.claude/skills/<name>/SKILL.md` with frontmatter
2. Add `"<name>": "description"` to `bundled_skills()` in `src/erk/capabilities/skills/bundled.py`
3. Add `"<name>"` to `codex_portable_skills()` in `src/erk/core/capabilities/codex_portable.py`
4. Add force-include entry in `pyproject.toml`:
   `".claude/skills/<name>" = "erk/data/claude/skills/<name>"`

### New Bundled + Portable + Required Skill (4 file touches + 1 extra line)

Same as above, plus add `"<name>"` to `_REQUIRED_BUNDLED_SKILLS` in `bundled.py`.

## Common Mistakes

- **Forgetting portability classification**: Every skill must be in exactly one of `codex_portable_skills()` or `claude_only_skills()`. Tests will fail if a skill is in neither or both.
- **Forgetting bundle classification**: Every skill must be in exactly one of `bundled_skills()` or `_UNBUNDLED_SKILLS`. Same rule.
- **Name mismatch**: The `name` in SKILL.md frontmatter must exactly match the directory name.
- **Missing force-include**: Bundled skills need a pyproject.toml entry or wheel builds won't include the skill content.
