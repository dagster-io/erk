---
title: Adding Skill Capabilities
read_when:
  - "adding skill capabilities"
  - "creating new skills for external projects"
  - "understanding SkillCapability pattern"
last_audited: "2026-02-03"
audit_result: edited
---

# Adding Skill Capabilities

Skills are capabilities that install `.claude/skills/<name>/` directories to external projects. They use the `SkillCapability` base class.

## Implementation Checklist

1. **Create capability file** at `src/erk/capabilities/skills/<name>.py`
   - Extend `SkillCapability`
   - Implement `skill_name` property (directory name under `.claude/skills/`)
   - Implement `description` property
   - See `src/erk/capabilities/skills/dignified_python.py` for canonical example (~16 lines)

2. **Register** in `src/erk/core/capabilities/registry.py`
   - Add import
   - Add instance to `_all_capabilities()` tuple

3. **Bundle skill content** at `src/erk/bundled/.claude/skills/<name>/`
   - Main skill document plus optional supporting files

4. **Verify** with `erk init capability list`

## Key Details

- **Bundled artifacts path**: `src/erk/bundled/.claude/skills/<name>/` — this non-obvious path is where the skill content must exist for installation to work
- **Silent failure warning**: If the bundled content directory is missing, `install()` will silently produce an empty skill directory with no error

## Related Documentation

- [Adding New Capabilities](adding-new-capabilities.md) - General capability pattern
