# Documentation Plan: Bundled .codex/ Artifact Source

## Context

This PR implements the infrastructure layer for bundling Codex-portable skills within erk wheels. The goal is to enable erk to distribute skills that work with generic AI coding agents (like OpenAI's Codex) in addition to Claude-specific skills. This is Step 1.2 of Objective #6632.

The implementation introduced a two-tier skill classification system: **Codex-portable skills** (12 skills that work with any AI agent) and **Claude-only skills** (4 skills requiring Claude-specific features). A new `get_bundled_codex_dir()` function provides path resolution that handles both wheel installs (bundled at `erk/data/codex/`) and editable installs (falls back to `.claude/`).

Documentation matters because:

1. **Future skill authors** need to understand the portability criteria when creating new skills
2. **Maintenance agents** need to know how to add/remove skills from the registry and update pyproject.toml mappings
3. **TOML constraint awareness** is critical - the implementation discovered that TOML dictionaries cannot have duplicate keys, which forced a strategic pivot in the bundling approach

## Raw Materials

https://gist.github.com/schrockn/73f011f3f462843f7800f873f3179fd7

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 4     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Codex Skill Portability Registry

**Location:** `docs/learned/architecture/bundled-artifacts.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl], [PR #6648]

**Draft Content:**

Add to bundled-artifacts.md:

```markdown
## Codex Portability Classification

Erk classifies skills into two tiers for external distribution:

### Codex-Portable Skills

Skills that work with any AI coding agent. These have no Claude-specific dependencies (hooks, session logs, Claude Code commands).

See `CODEX_PORTABLE_SKILLS` in `src/erk/core/capabilities/codex_portable.py` for the authoritative list (12 skills).

**Portability Criteria:**

- No Claude-specific hook dependencies
- No session log parsing or storage
- No Claude Code slash commands
- YAML frontmatter with `name` (<=64 chars) and `description` (<=1024 chars)

### Claude-Only Skills

Skills requiring Claude-specific features. These cannot be ported.

See `CLAUDE_ONLY_SKILLS` in `src/erk/core/capabilities/codex_portable.py` for the list (4 skills).

**Why Claude-only:** Session inspection, CI iteration hooks, command/skill creators that output Claude format

### Bundled Path Resolution

| Install Type | `get_bundled_codex_dir()` Returns |
| ------------ | --------------------------------- |
| Wheel        | `erk/data/codex/`                 |
| Editable     | `.claude/` (shared with Claude)   |

See `get_bundled_codex_dir()` in `src/erk/artifacts/paths.py` for the implementation.

### Adding a New Codex-Portable Skill

1. Create skill in `.claude/skills/<name>/SKILL.md` with required frontmatter
2. Add skill name to `CODEX_PORTABLE_SKILLS` in `src/erk/core/capabilities/codex_portable.py`
3. Add force-include mapping in `pyproject.toml` under `[tool.hatch.build.targets.wheel.force-include]`
4. Run tests: `pytest tests/unit/artifacts/test_codex_compatibility.py`
```

---

### MEDIUM Priority

#### 1. TOML Force-Include Mapping Pattern

**Location:** `docs/learned/reference/toml-handling.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add section on Hatchling force-include mappings:

````markdown
## Hatchling Force-Include Mappings

When bundling files in wheels via `pyproject.toml`, use the `[tool.hatch.build.targets.wheel.force-include]` section.

### Critical Constraint: No Duplicate Keys

TOML dictionaries cannot have duplicate keys. If you need to map the same source file to multiple destinations, you cannot do this:

```toml
# WRONG - TOML parse error (duplicate key)
[tool.hatch.build.targets.wheel.force-include]
".claude/skills/foo" = "erk/data/claude/skills/foo"
".claude/skills/foo" = "erk/data/codex/skills/foo"
```
````

**Workarounds:**

1. Use a build script to copy files post-build
2. Choose a single canonical destination (preferred for simplicity)
3. Restructure source to avoid the conflict

### Pattern: Skill Bundling

See the force-include section in `pyproject.toml` for the canonical mapping pattern for Codex-portable skills. All 15 Codex-portable skills map to a single `erk/data/codex/skills/` destination in wheels.

````

---

#### 2. Codex Frontmatter Validation Tests

**Location:** `docs/learned/testing/codex-frontmatter-validation.md` (CREATE)
**Action:** CREATE
**Source:** [Impl], [PR #6648]

**Draft Content:**

```markdown
---
title: Codex Frontmatter Validation Tests
read_when:
  - adding new skills to the codebase
  - debugging skill validation failures
  - understanding YAML frontmatter requirements
---

# Codex Frontmatter Validation Tests

Layer 3 pure unit tests validate that all skills maintain Codex compatibility.

## Test Coverage

See test functions in `tests/unit/artifacts/test_codex_compatibility.py`:

| Test | What It Validates |
| ---- | ----------------- |
| `test_all_skills_have_codex_required_frontmatter()` | All skills have `name` (<=64 chars) and `description` (<=1024 chars) |
| `test_portable_skills_match_bundled()` | All `CODEX_PORTABLE_SKILLS` exist and have valid frontmatter |
| `test_codex_portable_and_claude_only_cover_all_skills()` | No orphaned or duplicate skills in registries |
| `test_claude_only_skills_exist()` | All `CLAUDE_ONLY_SKILLS` exist in `.claude/skills/` |

## Frontmatter Requirements

All skill `SKILL.md` files must have YAML frontmatter with:

- `name`: String, max 64 characters
- `description`: String, max 1024 characters

## Common Failures

**Orphan skill detected:** A skill directory exists in `.claude/skills/` but is not listed in either `CODEX_PORTABLE_SKILLS` or `CLAUDE_ONLY_SKILLS`. Add it to the appropriate registry.

**Missing frontmatter:** The `SKILL.md` file lacks the required `name` or `description` fields. Add them to the YAML frontmatter block.

**File naming:** Use `SKILL.md` (uppercase), not `skill.md`.
````

---

### LOW Priority

#### 1. Skill Naming Convention Enforcement

**Location:** `docs/learned/conventions.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to conventions.md:

```markdown
## Skill File Naming

Skill directories must use the standard filename `SKILL.md` (uppercase). The validation tests will fail for skills using `skill.md` or other variants.

**Correct:** `.claude/skills/my-skill/SKILL.md`
**Wrong:** `.claude/skills/my-skill/skill.md`
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. TOML Duplicate Key Error

**What happened:** Initial implementation attempted to map the same source file (`.claude/skills/X`) to two destinations (`erk/data/claude/skills/X` and `erk/data/codex/skills/X`) in the pyproject.toml force-include section.

**Root cause:** TOML specification prohibits duplicate keys in the same table. The parse error occurred immediately during pytest discovery.

**Prevention:** Document the TOML duplicate key constraint in `docs/learned/reference/toml-handling.md`. When bundling to multiple destinations, use alternative approaches (build scripts, single canonical location, or restructured sources).

**Recommendation:** ADD_TO_DOC (added above)

### 2. Skill Frontmatter Drift

**What happened:** The `cli-skill-creator` skill used `skill.md` instead of `SKILL.md`, causing inconsistency.

**Root cause:** No automated enforcement of file naming conventions for skills.

**Prevention:** The new validation tests (`test_codex_compatibility.py`) now enforce that all skills have properly named `SKILL.md` files with required frontmatter.

**Recommendation:** CONTEXT_ONLY (tests now prevent this)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. TOML Duplicate Key Prevention

**Score:** 5/10 (Non-obvious +2, Significant time cost +2, Cross-cutting +1)

**Trigger:** Before editing `pyproject.toml` force-include sections or any TOML mapping tables

**Warning:** TOML dictionaries cannot have duplicate keys. If you need to map one source to multiple destinations, use a build script or choose a single canonical location.

**Target doc:** `docs/learned/reference/toml-handling.md`

This is tripwire-worthy because:

- The constraint is not intuitive for developers familiar with Python dicts
- The error manifests during build/test, not immediately when editing
- Debugging requires understanding TOML spec, not just Python
- The session lost time discovering this constraint empirically

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Skill SKILL.md Naming

**Score:** 2/10 (Single-location fix +1, Now caught by tests +1)

**Notes:** The validation tests now catch this automatically. Would only warrant a tripwire if naming errors become frequent despite test coverage. Currently low priority because the test suite provides immediate feedback.

---

## Implementation Notes for Step 1.4

Step 1.4 (install dispatch) will consume this infrastructure to copy skills to target repositories. Key considerations:

1. **Import path:** `from erk.core.capabilities.codex_portable import CODEX_PORTABLE_SKILLS`
2. **Source directory:** Call `get_bundled_codex_dir()` from `src/erk/artifacts/paths.py`
3. **Destination:** Copy to `.codex/skills/` in the target repository
4. **Iteration pattern:** Loop over `CODEX_PORTABLE_SKILLS` and copy each skill directory
5. **File structure:** Each skill is a directory containing `SKILL.md` (may have additional files)

The infrastructure handles wheel vs editable install detection transparently - Step 1.4 just needs to read from `get_bundled_codex_dir()` and iterate over the skill names in the registry.
