# Plan: Bundled `.codex/` Artifact Source (Objective #6632, Step 1.2)

## Goal

Create the infrastructure for erk to bundle and resolve Codex-compatible skill artifacts, so that Step 1.4 (install dispatch) can copy skills to `.codex/skills/` in target repos.

## Design Decision: No Separate `.codex/` Source Directory

All existing Claude skills already have the required Codex YAML frontmatter (`name` and `description`). The file format is identical. Rather than duplicating files into a `.codex/` directory, we:

1. Add a `get_bundled_codex_dir()` path function that resolves the bundled Codex artifacts
2. For **editable installs**: Point to a `.codex/` directory at the repo root (created as a lightweight directory containing only a `skills/` symlink or actual skill copies)
3. For **wheel installs**: Use `pyproject.toml` `force-include` to map `.claude/skills/X` → `erk/data/codex/skills/X`
4. Add a validation test ensuring all skills maintain Codex frontmatter compatibility

**Key insight**: The wheel `force-include` approach means we can map the same `.claude/skills/` source files to _both_ `erk/data/claude/skills/` and `erk/data/codex/skills/` without any build scripts or file duplication in the repo.

**For editable installs**: `get_bundled_codex_dir()` returns the `.claude/` parent directory remapped -- but actually, the simpler approach is to just have the install logic (Step 1.4) read from `get_bundled_claude_dir()` and write to `.codex/skills/` in the target. This step's job is just to ensure:

- The path function exists for wheel installs
- The wheel includes codex-formatted artifacts
- All skills pass Codex frontmatter validation

## Implementation

### 1. Add `get_bundled_codex_dir()` to `src/erk/artifacts/paths.py`

```python
@cache
def get_bundled_codex_dir() -> Path:
    erk_package_dir = _get_erk_package_dir()
    if _is_editable_install():
        # Editable: skills come from .claude/ (format-compatible)
        # The install step copies to .codex/ in the target repo
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".claude"  # Same source, different target
    # Wheel install: data is bundled at erk/data/codex/
    return erk_package_dir / "data" / "codex"
```

**Wait -- this is confusing.** If `get_bundled_codex_dir()` returns `.claude/` for editable installs, it defeats the purpose. The cleaner approach:

**Revised**: Don't create `get_bundled_codex_dir()` at all in this step. Instead:

- The skill source is always `get_bundled_claude_dir() / "skills" / skill_name`
- The install _target_ is determined by backend: `.claude/skills/` or `.codex/skills/`
- For wheel installs, we still need the codex force-include entries (so the wheel carries codex-packaged artifacts for non-editable users)

**Final approach**: This step delivers:

1. Codex force-include entries in `pyproject.toml` for wheel distribution
2. Frontmatter validation test
3. A `codex_portable_skills()` function that returns the list of skills suitable for Codex

### 2. Update `pyproject.toml` force-include for Codex

Add entries mapping Claude skills to Codex data directory:

```toml
# Codex skills (same source files, Codex-compatible frontmatter)
".claude/skills/dignified-python" = "erk/data/codex/skills/dignified-python"
".claude/skills/learned-docs" = "erk/data/codex/skills/learned-docs"
".claude/skills/erk-diff-analysis" = "erk/data/codex/skills/erk-diff-analysis"
```

**File**: `pyproject.toml` (lines ~60-75)

### 3. Add `get_bundled_codex_dir()` to `src/erk/artifacts/paths.py`

For wheel installs, we need a path resolver:

```python
@cache
def get_bundled_codex_dir() -> Path:
    """Get path to bundled .codex/ directory.

    For wheel installs: bundled at erk/data/codex/
    For editable installs: falls back to .claude/ (same format).
    """
    erk_package_dir = _get_erk_package_dir()
    if _is_editable_install():
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".claude"
    return erk_package_dir / "data" / "codex"
```

Note: For editable installs, this returns `.claude/` since the file formats are identical. The install step (1.4) handles the target directory mapping.

### 4. Create Codex skill portability registry

**New file**: `src/erk/core/capabilities/codex_portable.py`

```python
"""Registry of skills portable to Codex CLI."""

# Skills that work with any AI coding agent (not Claude-specific)
CODEX_PORTABLE_SKILLS: frozenset[str] = frozenset({
    "dignified-python",
    "fake-driven-testing",
    "erk-diff-analysis",
    "erk-exec",
    "erk-planning",
    "objective",
    "gh",
    "gt",
    "learned-docs",
    "dignified-code-simplifier",
    "pr-operations",
    "pr-feedback-classifier",
})

# Skills that reference Claude-specific features (hooks, session logs, commands)
CLAUDE_ONLY_SKILLS: frozenset[str] = frozenset({
    "session-inspector",
    "ci-iteration",
    "command-creator",
})
```

### 5. Add frontmatter validation test

**New file**: `tests/unit/artifacts/test_codex_compatibility.py`

Tests:

- `test_all_skills_have_codex_required_frontmatter` -- every SKILL.md has `name` (≤64 chars) and `description` (≤1024 chars)
- `test_portable_skills_match_bundled` -- every skill in `CODEX_PORTABLE_SKILLS` exists in `.claude/skills/`
- `test_codex_portable_and_claude_only_cover_all_skills` -- union equals all skills (no orphans)

### 6. Export `get_bundled_codex_dir` from sync module

**File**: `src/erk/artifacts/sync.py` -- add import of `get_bundled_codex_dir` alongside existing imports (for downstream use by Step 1.4).

## Files to Modify

| File                                               | Change                               |
| -------------------------------------------------- | ------------------------------------ |
| `src/erk/artifacts/paths.py`                       | Add `get_bundled_codex_dir()`        |
| `src/erk/core/capabilities/codex_portable.py`      | New: portability registry            |
| `pyproject.toml`                                   | Add Codex force-include entries      |
| `tests/unit/artifacts/test_codex_compatibility.py` | New: frontmatter + portability tests |

## Verification

1. Run `pytest tests/unit/artifacts/test_codex_compatibility.py` -- all frontmatter validation passes
2. Run `uv build` and inspect wheel contents -- verify `erk/data/codex/skills/` contains expected skills
3. Run `python -c "from erk.artifacts.paths import get_bundled_codex_dir; print(get_bundled_codex_dir())"` -- returns valid path
