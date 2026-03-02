---
title: Artifact Distribution Sync Testing
read_when:
  - "adding portable skills to codex_portable_skills()"
  - "modifying pyproject.toml force-include entries"
  - "understanding bundled skill testing and distribution"
tripwires:
  - action: "adding a skill to codex_portable_skills() without a pyproject.toml force-include entry"
    warning: "The wheel won't contain the skill. Add a force-include entry in pyproject.toml [tool.hatch.build.targets.wheel.force-include]. test_codex_portable_skills_match_force_include will catch this."
  - action: "adding a force-include entry without registering in codex_portable_skills()"
    warning: "The skill will be distributed but not recognized by the runtime. Add it to codex_portable_skills() in src/erk/core/capabilities/codex_portable.py."
---

# Artifact Distribution Sync Testing

The artifact distribution tests enforce bidirectional synchronization between the Python skill registry and the wheel build manifest. This prevents shipping skills that aren't registered or registering skills that aren't packaged.

## Three-Layer Validation Pyramid

<!-- Source: tests/unit/artifacts/test_codex_compatibility.py -->

```
Layer 1: Frontmatter Validation
├── test_all_skills_have_codex_required_frontmatter()
└── Every SKILL.md has valid name (≤64 chars) and description (≤1024 chars)

Layer 2: On-Disk Inventory
├── test_portable_skills_match_bundled()
├── test_claude_only_skills_exist()
├── test_codex_portable_and_claude_only_cover_all_skills()
└── All registered skills exist on disk, no orphans, no duplicates

Layer 3: Distribution Consistency
└── test_codex_portable_skills_match_force_include()
    ├── portable_skills - force_included → missing from wheel
    ├── force_included - portable_skills → extra in wheel
    └── Fails with actionable remediation instructions
```

## Key Components

### Source of Truth: codex_portable_skills()

<!-- Source: src/erk/core/capabilities/codex_portable.py -->

The `codex_portable_skills()` function in `src/erk/core/capabilities/codex_portable.py` returns a `frozenset[str]` of skill names that should be distributed in the wheel. This is the authoritative registry.

A separate `claude_only_skills()` function lists skills that use Claude-specific features and are NOT distributed.

### Build Manifest: pyproject.toml force-include

<!-- Source: pyproject.toml, [tool.hatch.build.targets.wheel.force-include] -->

The `[tool.hatch.build.targets.wheel.force-include]` section maps source paths to wheel paths:

```toml
".claude/skills/dignified-python" = "erk/data/codex/skills/dignified-python"
".claude/skills/fake-driven-testing" = "erk/data/codex/skills/fake-driven-testing"
```

### TOML Parsing: \_get_force_included_skill_names()

The test helper parses `pyproject.toml` via `tomllib`, extracts entries matching the `.claude/skills/` prefix, and filters out nested paths with `"/" not in skill_name`. This prevents nested subdirectories from matching as skill names.

## Sync Test: test_codex_portable_skills_match_force_include()

Computes the symmetric difference between the two sets and fails with direction-specific messages:

- **Missing from pyproject.toml**: "Add force-include entries for these skills in pyproject.toml"
- **Extra in pyproject.toml**: "Add these to codex_portable_skills() or remove the force-include entries"

## Troubleshooting

| Symptom                                      | Cause                                                   | Fix                                                     |
| -------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| Test fails: "missing from pyproject.toml"    | Added to `codex_portable_skills()` but not wheel config | Add force-include entry to `pyproject.toml`             |
| Test fails: "not in codex_portable_skills()" | Added force-include but not registered                  | Add to `codex_portable_skills()` in `codex_portable.py` |
| Test fails: "skill not found on disk"        | Registered but directory doesn't exist                  | Create `.claude/skills/<name>/SKILL.md`                 |
| Test fails: frontmatter validation           | SKILL.md missing or malformed                           | Add `name` and `description` to SKILL.md frontmatter    |

## Related Documentation

- [ErkPackageInfo Value Object](erk-package-info-pattern.md) — How bundled paths are resolved at runtime
