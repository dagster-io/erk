# Extraction Plan: Kit Artifact Path Conventions

## Objective

Document the two artifact path formats used in the kit system and when each is used.

## Source Information

- Session ID: 0e122c65-d791-4064-a640-c7cc0e279e16
- Branch: P3028-fix-kit-install-dev-mode-12-11-2000

## Documentation Items

### Item 1: Kit Artifact Path Formats

**Type:** Category A (Learning Gap)
**Location:** docs/agent/kits/ (new section or update existing)
**Action:** Add documentation
**Priority:** Medium

**Context:**
During implementation of the dev mode artifact detection fix, discovered that the kit system uses two different path formats for artifacts:

1. **Manifest paths** (in kit.yaml): Relative paths without base directory prefix
   - Example: `agents/helper.md`, `skills/tool/SKILL.md`
   
2. **Installed paths** (in kits.toml): Full paths with base directory prefix
   - Example: `.claude/agents/helper.md`, `.github/workflows/kit/ci.yml`

The `ARTIFACT_TARGET_DIRS` mapping in `dot_agent_kit.models.artifact` defines which base directory each artifact type uses:
- Most types (skill, command, agent, hook, doc) → `.claude/`
- workflow → `.github/`

**Draft Content:**

```markdown
## Artifact Path Formats

The kit system uses two path formats for artifacts:

### Manifest Paths (kit.yaml)

Paths in `kit.yaml` are relative to the kit's artifacts directory and do NOT include the base directory prefix:

```yaml
artifacts:
  agent:
    - agents/my-kit/helper.md      # NOT .claude/agents/...
  skill:
    - skills/my-kit/tool/SKILL.md  # NOT .claude/skills/...
  workflow:
    - workflows/my-kit/ci.yml      # NOT .github/workflows/...
```

### Installed Paths (kits.toml)

Paths tracked in `kits.toml` include the full base directory prefix:

```toml
[kits.my-kit]
artifacts = [
    ".claude/agents/my-kit/helper.md",
    ".claude/skills/my-kit/tool/SKILL.md",
    ".github/workflows/my-kit/ci.yml"
]
```

### Path Conversion

Use `compare_artifact_lists()` from `dot_agent_kit.commands.check` when comparing manifest artifacts against installed artifacts. This function handles the path prefix conversion automatically using `ARTIFACT_TARGET_DIRS`.

**Do NOT** manually compare manifest paths to installed paths - they will never match due to the prefix difference.
```

**Rationale:**
This would have prevented the bug where `_all_artifacts_are_symlinks()` was comparing paths incorrectly. Future developers working on kit artifact handling will know to use the existing utility function.