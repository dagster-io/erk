# Create module-to-subpackage skill

## Context

During a session splitting `test_capabilities.py` (1,972 lines) into 11 submodules, we identified a repeatable process for converting monolithic Python modules into subpackages. This skill captures that process so agents can execute it reliably on any large module.

## Plan

Create `.claude/skills/module-to-subpackage/SKILL.md` with the following content:

---

```yaml
---
name: module-to-subpackage
description: >
  Guide for converting a monolithic Python module into a subpackage with submodules.
  Use when breaking apart a large .py file into a directory of smaller modules,
  splitting a module into a package, reorganizing a single file into subdirectories,
  or when a user says things like "split this module", "break this file apart",
  "convert to subpackage", or "this file is too big". Also use when a user identifies
  a large Python file and wants to reorganize it without changing behavior.
---
```

# Module to Subpackage

Convert a monolithic Python module into a subpackage with submodules while preserving all behavior. This is a pure mechanical reorganization — no logic changes, no fixes to pre-existing issues, no improvements.

## Core Principle: Pure Reorg

This refactoring must be behavior-preserving. Copy code verbatim. Do not:
- Fix pre-existing lint/style issues (they'll show up in review — resolve as "pre-existing")
- Rename functions or change signatures
- "Improve" code while moving it
- Add or remove functionality

The goal is a clean diff that only moves code between files. Reviewers should be able to verify the split is correct by confirming every line in the old file appears in exactly one new file.

## Phase 1: Structural Inventory

Understand the monolith before designing the split.

**Scan for boundaries:**
```bash
# Section headers and definitions with line numbers
grep -n "^# ==\|^class \|^def " <file>
```

**Capture:**
- All section comment blocks (these are natural split boundaries)
- All class definitions and their line ranges
- All top-level function definitions
- All imports at the top of the file
- Total count of top-level definitions (classes + functions)
- Any module-level helpers or constants

**Why this matters:** Section headers placed by the original author reveal the intended logical grouping. Classes and functions without headers between them likely belong together.

## Phase 2: Target Discovery

Check if the destination already has structure.

**Check for existing subpackage:**
```bash
# If splitting foo.py, check for foo/ directory
ls <target_directory>/
```

**Determine:**
- Does the target directory already exist? (common for test files)
- Are there existing files that overlap with planned new files?
- Is there an `__init__.py`? (required for test directories in this project)
- What patterns do existing files in the directory follow?

**If existing files overlap:** You'll need to merge in Phase 5 rather than create fresh.

## Phase 3: Grouping Design

Map sections of the monolith to new files. Present this as a table for user review before proceeding.

**Grouping heuristics (in priority order):**
1. **Author's sections** — Comment headers like `# === Tests for Foo ===` are the strongest signal
2. **Feature cohesion** — Code testing/implementing the same feature belongs together
3. **Import cohesion** — Code sharing the same specialized imports likely belongs together
4. **Size balance** — Avoid files with fewer than ~20 lines (merge with a neighbor) or more than ~500 lines (split further)

**File naming:** Match the concept being grouped, not the original file name.
- `test_capabilities.py` → `test_workflows.py`, `test_permissions.py`, `test_registry.py`
- `utils.py` → `string_utils.py`, `path_utils.py`, `date_utils.py`

**Present a mapping table:**

| New file | Sections (line ranges) | What it contains | ~Lines |
|---|---|---|---|
| `test_base.py` | CapabilityResult (47-58), ... | Core data structures | ~100 |
| ... | ... | ... | ... |

## Phase 4: Shared Code Placement

Identify code used across multiple sections and decide where it lives.

**Types of shared code:**
- Helper functions (e.g., `_write_state_toml()`)
- Helper classes (e.g., `_TestCapability`)
- Constants and fixtures
- Module-level configuration

**Placement rules:**
- **1 consumer** → place in that consumer's file
- **2 consumers** → place in the primary consumer's file (the one that uses it more)
- **3+ consumers** → consider a `_helpers.py` or `conftest.py` (for test fixtures), but only if truly necessary. Duplication across 2-3 files is often preferable to an artificial shared module.

## Phase 5: Execution

### Create new files

For each file in the mapping:
1. Write the module docstring (brief, describes what this file tests/contains)
2. Add only the imports needed by the functions in this file
3. Copy the functions/classes verbatim from the monolith
4. Preserve section comment headers within the file

### Merge into existing files

When a target file already exists:
1. Read the existing file completely
2. Compare tests/functions by **behavior**, not by name — two functions testing the same thing with different names are duplicates
3. Append only non-duplicate code to the end of the existing file
4. Add appropriate section headers to separate old and new content

### Fix mechanical issues

After creating all files:
```bash
# Fix import sorting (the most common issue after splitting)
uv run ruff check --fix <new_files>
```

### Delete the original

Only after all new files are created and verified:
```bash
rm <original_monolith.py>
```

## Phase 6: Verification

**Count definitions:**
```bash
# Before (from git history or memory)
grep -c "^def \|^class " <original_file>

# After (across all new files)
grep -rch "^def \|^class " <new_files> | paste -sd+ - | bc
```

The after count should equal or exceed the before count (excess comes from pre-existing files that were merged into).

**Check for dangling references:**
```bash
# Ensure nothing imports or references the deleted file
grep -r "<original_module_name>" <project_root>
```

**Run tests and linter** (use devrun agent):
- Run the test suite for the affected directory
- Run linter checks
- Run type checker

## Phase 7: PR Workflow

### Pure reorg discipline

When review comments flag issues in the moved code:
- If the issue existed in the original file → resolve as pre-existing
- Reply: "Pre-existing: this [issue] was copied verbatim from the original `<file>`. Not addressing in this pure reorg PR."
- Then resolve the thread

**Load the pr-operations skill** (`@.claude/skills/pr-operations/`) for correct thread resolution commands. Key points:
- Use `erk exec get-pr-review-comments` to fetch threads with proper thread IDs
- Use `erk exec resolve-review-thread --thread-id <PRRT_id> --comment "..."` to reply AND resolve
- Use `erk exec resolve-review-threads` for batch resolution
- Never use raw `gh api` for thread operations (replies without resolving)

### Commit message

Format: `Split <module> into <subpackage> subpackage (#<PR>)`

The PR description should include:
- The mapping table from Phase 3
- Before/after definition counts
- Note that this is a pure reorg with no behavior changes

---

## Registration

Register as unbundled + claude-only (3 file touches per erk-skill-onboarding):

| File | Change |
|------|--------|
| `.claude/skills/module-to-subpackage/SKILL.md` | Create (skill content above) |
| `src/erk/capabilities/skills/bundled.py` | Add `"module-to-subpackage"` to `_UNBUNDLED_SKILLS` |
| `src/erk/core/capabilities/codex_portable.py` | Add `"module-to-subpackage"` to `claude_only_skills()` |

No `pyproject.toml` changes needed (unbundled skills skip force-include).

## Verification

- Run `make fast-ci` via devrun agent to confirm registration tests pass
- Verify skill frontmatter parses (name matches directory, description present)