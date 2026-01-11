# Plan: Document Autolearn Feature

> **Replans:** #4690

## What Changed Since Original Plan

- PR #4704 (the documentation PR) was **closed without merging** - only contained `.worker-impl/` plan files, no actual documentation
- The autolearn feature implementation (PR #4684) remains complete and merged
- All 4 documentation items from the original plan are still needed

## Investigation Findings

### Corrections to Original Plan

- Config file format is **TOML** (`~/.erk/config.toml`), not YAML as mentioned in the plan

### Additional Details Discovered

- Default value: `autolearn: bool = False` in GlobalConfig (types.py line 148)
- Learn plan detection uses `erk-learn` label check via `_is_learn_plan()` function
- Title format: Creates "Learn: {source_title}" with `[erk-learn]` suffix
- Three call sites in land_cmd.py: `_land_current_branch()`, `_land_specific_pr()`, `_land_by_branch()`
- CLI flag syntax: `--autolearn/--no-autolearn` with `autolearn_flag` parameter name
- Fail-open pattern: All error paths return None with yellow warning, never blocking land

## Remaining Gaps

All 4 documentation items from the original plan are still needed:

1. **docs/learned/erk/index.md** - No autolearn entry
2. **docs/learned/erk/autolearn.md** - File does not exist
3. **docs/learned/planning/lifecycle.md** - No autolearn mention
4. **docs/learned/cli/index.md** - No --no-autolearn documentation

## Implementation Steps

### 1. Create docs/learned/erk/autolearn.md

Create comprehensive documentation covering:

```markdown
---
description: Automatic learn plan creation when landing PRs
read_when: Working with autolearn, configuring erk land behavior, understanding learn plans
category: erk
---

# Autolearn

## Overview
Autolearn automatically creates a learn plan issue when landing a PR via `erk land`. This captures session insights before they're lost.

## Configuration
Enable in `~/.erk/config.toml`:
```toml
autolearn = true
```

Default: disabled (`false`)

## CLI Override
- `erk land --no-autolearn` - Skip autolearn for this landing
- `erk land --autolearn` - Force enable even if config disabled

## Behavior
- **Trigger condition**: Only for PRs from plan branches (branch name starts with `P{issue}-`)
- **Skip condition**: Source issue already has `erk-learn` label (prevents recursive learns)
- **Fail-open**: Errors warn but never block the landing operation
- **Output**: Creates issue titled "Learn: {source_title}" with `[erk-learn]` suffix

## Implementation Details
- Core logic: `src/erk/cli/commands/autolearn.py`
- Integration: Three call sites in `land_cmd.py`
- Config: `GlobalConfig.autolearn` field in types.py
```

### 2. Update docs/learned/erk/index.md

Add entry for autolearn.md to the erk features index.

### 3. Update docs/learned/planning/lifecycle.md

Add autolearn as a post-land step in Phase 5 (Finalization & Merge):

> After PR merges, if autolearn is enabled, a learn plan issue is automatically created to capture session insights for later extraction.

### 4. Update docs/learned/cli/index.md

Document the `--autolearn/--no-autolearn` flag under the `erk land` command section (if one exists) or add a note about CLI flags that override config.

## Critical Files

- `docs/learned/erk/autolearn.md` (create)
- `docs/learned/erk/index.md` (update)
- `docs/learned/planning/lifecycle.md` (update)
- `docs/learned/cli/index.md` (update)

## Verification

1. Run `erk docs sync` to regenerate index files
2. Verify all cross-references resolve correctly
3. Check frontmatter is valid YAML with required fields (description, read_when, category)