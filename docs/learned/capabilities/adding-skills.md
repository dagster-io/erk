---
title: Adding Skill Capabilities
read_when:
  - "adding skill capabilities"
  - "creating new skills for external projects"
  - "understanding SkillCapability pattern"
tripwires:
  - action: "creating a skill capability"
    warning: "Bundled content directory must exist or install() silently creates empty skill directory. See silent failure modes below."
  - action: "skill not appearing in erk init capability list"
    warning: "For bundled skills, add entry to bundled_skills() dict in src/erk/capabilities/skills/bundled.py. For custom capabilities, import AND instantiate in registry.py _all_capabilities() tuple."
last_audited: "2026-02-16 02:45 PT"
audit_result: edited
---

# Adding Skill Capabilities

Skills are capabilities that install `.claude/skills/<name>/` directories to external projects. The `SkillCapability` base class handles all implementation mechanics, making skill creation a two-property exercise.

## Why SkillCapability Exists

<!-- Source: src/erk/core/capabilities/skill_capability.py, SkillCapability class -->

The base class exists because skill installation follows an invariant pattern:

1. Check if `.claude/skills/{skill_name}/` exists
2. Locate bundled content at `{bundled_root}/skills/{skill_name}/`
3. Copy directory tree to target project
4. Record installation in `.erk/state.toml`

Subclasses only declare **which** skill to install, not **how** to install it. This eliminates ~100 lines of boilerplate per skill.

## Decision Context: When to Use SkillCapability

Use `SkillCapability` when you're installing a **single** skill directory with standard structure. If you need:

- Multiple skills in one capability → Use direct `Capability` subclass
- Custom installation logic → Use direct `Capability` subclass
- File modification after copy → Use direct `Capability` subclass

For the 90% case (one skill, standard install), `SkillCapability` is correct.

## Implementation: Four-Step Pattern

### 1. Register in Bundled Skills Dict

<!-- Source: src/erk/capabilities/skills/bundled.py, bundled_skills -->

For simple skills (name + description only), add an entry to the `bundled_skills()` dict. See `bundled_skills()` in `src/erk/capabilities/skills/bundled.py` — it's a `dict[str, str]` mapping skill name to description. Add your entry as `"my-skill": "Brief description for CLI display"`.

**That's it.** The `BundledSkillCapability` class and `create_bundled_skill_capabilities()` factory handle instantiation. Registry picks them up via `*create_bundled_skill_capabilities()` spread in `_all_capabilities()`.

**When you need custom logic**: Create a dedicated capability class (like `LearnedDocsCapability`) that subclasses `SkillCapability` directly and register it individually in `registry.py`.

### 2. No Manual Registry Step Needed

<!-- Source: src/erk/core/capabilities/registry.py, _all_capabilities -->

Bundled skills are automatically registered via the factory spread. See `_all_capabilities()` in `src/erk/core/capabilities/registry.py` — it includes `*create_bundled_skill_capabilities()` which picks up all entries from the `bundled_skills()` dict.

Adding to the `bundled_skills()` dict is sufficient — no import or instantiation needed in `registry.py`.

### 3. Bundle Skill Content

Create the actual skill content at `.claude/skills/{skill_name}/` in erk repo root. For editable installs, the capability system reads directly from repo root. For wheel installs, `pyproject.toml` bundles `.claude/` to `erk/data/claude/` during build.

<!-- Source: src/erk/artifacts/paths.py, get_bundled_claude_dir -->

**Critical:** The bundled directory path determines success. If `.claude/skills/my-skill/` doesn't exist:

- `install()` creates empty directory
- No error is raised
- User gets useless skill

### 4. Verify Installation

```bash
# Check registry visibility
erk init capability list | grep my-skill

# Install to test project
cd /path/to/test/project
erk init capability add my-skill

# Verify files copied
ls .claude/skills/my-skill/

# Verify state tracking
erk init capability list my-skill  # Should show "Installed: Yes"
```

## Silent Failure Modes

| Symptom                                             | Root Cause                                                          | Fix                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Capability not in `erk init capability list`        | Missing from `bundled_skills()` dict or `_all_capabilities()` tuple | Add to `bundled_skills()` in `bundled.py` (simple) or registry.py (custom)     |
| Empty skill directory created                       | Bundled content directory doesn't exist                             | Check `.claude/skills/{skill_name}/` exists in erk repo                        |
| Install succeeds but `is_installed()` returns False | State file corruption or race condition                             | Base class calls `add_installed_capability()`—check `.erk/state.toml` manually |
| Skill content out of date after edits               | Using wheel install, content frozen at build                        | Use editable install (`uv pip install -e .`) for development                   |

## How `skill_name` Property Works

<!-- Source: src/erk/core/capabilities/skill_capability.py, skill_name and name properties -->

The `skill_name` property determines:

1. **CLI identifier**: `erk init capability add {skill_name}`
2. **Bundled path**: `{bundled_root}/skills/{skill_name}/`
3. **Target path**: `.claude/skills/{skill_name}/`
4. **State tracking key**: Same as CLI identifier

The base class uses `skill_name` for both `name` (CLI identifier) and artifact paths, ensuring consistency.

## Relationship to Artifact Sync System

<!-- Source: src/erk/core/capabilities/skill_capability.py, install method -->

`SkillCapability.install()` delegates to the artifact sync system:

1. Calls `get_bundled_claude_dir()` to locate bundled content
2. Uses `_copy_directory()` for recursive copy with `shutil.copy2()`
3. Calls `add_installed_capability()` for state tracking

This delegation means skill capabilities inherit artifact sync behavior (preserving timestamps, handling symlinks, etc.) without reimplementing it.

## Related Documentation

- [Adding New Capabilities](adding-new-capabilities.md) - Base class decision table and registration mechanics
- [Bundled Artifacts System](../architecture/bundled-artifacts.md) - How editable vs wheel installs locate bundled content
- [Capability System Architecture](../architecture/capability-system.md) - State tracking and managed artifacts
