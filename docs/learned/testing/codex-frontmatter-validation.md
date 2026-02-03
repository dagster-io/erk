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

| Test                                                     | What It Validates                                                    |
| -------------------------------------------------------- | -------------------------------------------------------------------- |
| `test_all_skills_have_codex_required_frontmatter()`      | All skills have `name` (<=64 chars) and `description` (<=1024 chars) |
| `test_portable_skills_match_bundled()`                   | All `CODEX_PORTABLE_SKILLS` exist and have valid frontmatter         |
| `test_codex_portable_and_claude_only_cover_all_skills()` | No orphaned or duplicate skills in registries                        |
| `test_claude_only_skills_exist()`                        | All `CLAUDE_ONLY_SKILLS` exist in `.claude/skills/`                  |

## Frontmatter Requirements

All skill `SKILL.md` files must have YAML frontmatter with:

- `name`: String, max 64 characters
- `description`: String, max 1024 characters

## Common Failures

**Orphan skill detected:** A skill directory exists in `.claude/skills/` but is not listed in either `CODEX_PORTABLE_SKILLS` or `CLAUDE_ONLY_SKILLS`. Add it to the appropriate registry.

**Missing frontmatter:** The `SKILL.md` file lacks the required `name` or `description` fields. Add them to the YAML frontmatter block.

**File naming:** Use `SKILL.md` (uppercase), not `skill.md`.
