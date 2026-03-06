# Fix Unbundled Skill Test: Portability Registries Should Only Cover Bundled Skills

## Context

The `test_codex_portable_and_claude_only_cover_all_skills` test currently requires **every** skill on disk (in `.claude/skills/`) to appear in either `codex_portable_skills()` or `claude_only_skills()`. This forces unbundled skills (erk-repo-only skills not distributed in the wheel) to be listed in one of these portability registries, even though portability classification only matters for bundled skills that get synced to external projects.

The fix: portability registries (`codex_portable_skills()` and `claude_only_skills()`) should only cover **bundled** skills. Unbundled skills should be excluded from the portability test, and removed from the registries.

After this change, `claude_only_skills()` will be empty because all its current members are unbundled. This is correct — all currently bundled skills happen to be codex-portable.

## Changes

### 1. Remove unbundled skills from `claude_only_skills()`

**File**: `src/erk/core/capabilities/codex_portable.py`

Remove all entries from `claude_only_skills()`. Every skill currently listed (`cmux`, `session-inspector`, `ci-iteration`, `command-creator`, `cli-skill-creator`, `rename-swarm`, `erk-skill-onboarding`, `skill-creator`) is unbundled and should not be in this registry.

Return an empty `frozenset()`. Keep the function itself — it may gain bundled claude-only skills in the future, and it's referenced by tests and documentation.

Also remove `learned-docs` from `codex_portable_skills()` — it is an unbundled skill (listed in `_UNBUNDLED_SKILLS` in `bundled.py`).

**After changes:**

```python
@cache
def codex_portable_skills() -> frozenset[str]:
    """Skills that work with any AI coding agent (not Claude-specific)."""
    return frozenset(
        {
            "cli-push-down",
            "dignified-python",
            "fake-driven-testing",
            "erk-diff-analysis",
            "erk-exec",
            "erk-planning",
            "objective",
            "gh",
            "gt",
            "dignified-code-simplifier",
            "pr-operations",
            "pr-feedback-classifier",
        }
    )


@cache
def claude_only_skills() -> frozenset[str]:
    """Skills that reference Claude-specific features (hooks, session logs, commands)."""
    return frozenset()
```

### 2. Update `test_codex_portable_and_claude_only_cover_all_skills` to scope to bundled skills

**File**: `tests/unit/artifacts/test_codex_compatibility.py`

The test at line 172 currently uses `_get_all_skill_names()` (all skills on disk) as the universe. Change it to use only **bundled** skill names as the universe. The portability check should verify:

- Every **bundled** skill is in either `codex_portable_skills()` or `claude_only_skills()`
- No overlap between the two registries
- No entries in either registry that aren't bundled skills

Replace `all_skills = _get_all_skill_names()` with `all_skills = set(bundled_skills().keys())`.

Also update the orphan error message to reflect that the registries are only for bundled skills.

Also update the "nonexistent" check: instead of checking against skills-on-disk, check against bundled skills. If a skill is in a portability registry but not in `bundled_skills()`, that's an error.

**After changes:**

```python
def test_codex_portable_and_claude_only_cover_all_skills() -> None:
    """Verify union of codex_portable_skills() and claude_only_skills() equals all bundled skills.

    Portability classification only applies to bundled skills (those distributed
    in the wheel). Unbundled skills are excluded from this check.
    No bundled skills should be orphaned (missing from both registries).
    No skills should be duplicated (in both registries).
    """
    all_bundled = set(bundled_skills().keys())

    # Check for duplicates
    duplicates = codex_portable_skills() & claude_only_skills()
    if duplicates:
        pytest.fail(
            f"Skills in both codex_portable_skills() and claude_only_skills(): {sorted(duplicates)}"
        )

    # Check for orphans (bundled skills not in either registry)
    registered_skills = codex_portable_skills() | claude_only_skills()
    orphaned_skills = all_bundled - registered_skills

    if orphaned_skills:
        pytest.fail(
            f"Bundled skills not in codex_portable_skills() or claude_only_skills(): "
            f"{sorted(orphaned_skills)}\n"
            f"Add these to src/erk/core/capabilities/codex_portable.py\n"
            f"  codex_portable: works with any AI coding agent\n"
            f"  claude_only: references Claude-specific features"
        )

    # Check for entries in registries that aren't bundled skills
    non_bundled_portable = codex_portable_skills() - all_bundled
    non_bundled_claude = claude_only_skills() - all_bundled

    if non_bundled_portable or non_bundled_claude:
        failures = []
        if non_bundled_portable:
            failures.append(
                f"codex_portable_skills() contains non-bundled skills: "
                f"{sorted(non_bundled_portable)}"
            )
        if non_bundled_claude:
            failures.append(
                f"claude_only_skills() contains non-bundled skills: {sorted(non_bundled_claude)}"
            )
        pytest.fail("\n".join(failures))
```

### 3. Update `test_claude_only_skills_exist` to check against bundled skills

**File**: `tests/unit/artifacts/test_codex_compatibility.py`

The test at line 218 verifies all `claude_only_skills()` exist on disk. Since `claude_only_skills()` will now be empty, this test will trivially pass. Keep it as-is — it still validates correctness if claude-only bundled skills are added in the future.

No changes needed to this test.

### 4. Update `test_codex_portable_skills_match_force_include` — no changes needed

This test (line 230) already only checks `codex_portable_skills()` against pyproject.toml force-include entries. Since we're removing `learned-docs` from `codex_portable_skills()`, we need to verify there's no corresponding force-include entry for `learned-docs` in pyproject.toml. If there is, that's a separate concern (the test would catch it).

No source changes needed — the existing test will validate consistency.

## Files NOT Changing

- `src/erk/capabilities/skills/bundled.py` — `_UNBUNDLED_SKILLS`, `bundled_skills()`, and all related functions stay the same
- `pyproject.toml` — force-include entries are not affected (learned-docs shouldn't have one since it's unbundled)
- `.claude/skills/erk-skill-onboarding/SKILL.md` — documentation about the onboarding process. This references the portability registries but can be updated separately. The core behavior change is small enough that the existing onboarding docs still work (new unbundled skills just skip the portability step).
- Documentation in `docs/learned/` — these are non-blocking and can be updated separately

## Implementation Details

### Key decisions
- Keep `claude_only_skills()` as an empty function rather than deleting it. It's referenced in tests, documentation, and the onboarding skill. Deletion would be a larger change with no benefit.
- The module docstring in `codex_portable.py` remains accurate — it describes the purpose of both functions.
- `BundledSkillCapability.supported_backends` (in `bundled.py` line 90-94) doesn't need changes — it checks `codex_portable_skills()` and falls back to `("claude",)`. With `claude_only_skills()` empty, all bundled skills that aren't in `codex_portable_skills()` would get `("claude",)` backend. Currently that's zero skills, which is correct.

### Edge cases
- If a future bundled skill is Claude-only, add it to both `bundled_skills()` and `claude_only_skills()`. The tests will catch if it's missing from a portability registry.
- If a future unbundled skill is added, it only needs to go in `_UNBUNDLED_SKILLS`. No portability classification needed.

## Verification

1. Run the specific test file:
   ```
   pytest tests/unit/artifacts/test_codex_compatibility.py -v
   ```
   All tests should pass, including:
   - `test_codex_portable_and_claude_only_cover_all_skills` — now scoped to bundled skills
   - `test_bundled_and_unbundled_cover_all_skills` — unchanged, should still pass
   - `test_claude_only_skills_exist` — trivially passes with empty set
   - `test_codex_portable_skills_match_force_include` — should still pass

2. Run the full test suite to check for regressions:
   ```
   pytest tests/unit/ -v
   ```

3. Run type checker:
   ```
   ty check src/erk/core/capabilities/codex_portable.py tests/unit/artifacts/test_codex_compatibility.py
   ```