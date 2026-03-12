# Plan: Audit and Fix Outdated Skill Content

## Context

The `erk-planning` skill was just deleted for containing outdated content. This audit examined all 22 remaining skills distributed with erk. Four skills have confirmed issues ranging from wrong file paths to references to nonexistent files. The rest are clean.

## Audit Results Summary

| Skill | Status | Severity |
|-------|--------|----------|
| dignified-python | OK | - |
| **fake-driven-testing** | **NEEDS-UPDATE** | **MEDIUM** |
| erk-diff-analysis | OK | - |
| erk-exec | OK | - |
| objective | OK | - |
| gh | OK | - |
| gt | OK | - |
| dignified-code-simplifier | OK | - |
| pr-operations | OK | - |
| pr-feedback-classifier | OK | - |
| **ci-iteration** | **NEEDS-UPDATE** | **MEDIUM** |
| cli-skill-creator | OK | - |
| cmux | OK | - |
| command-creator | OK | - |
| learned-docs | OK | - |
| **session-inspector** | **NEEDS-UPDATE** | **HIGH** |
| erk-skill-onboarding | OK (minor) | LOW |
| refac-cli-push-down | OK | - |
| **refac-mock-to-fake** | **NEEDS-UPDATE** | **CRITICAL** |
| refac-module-to-subpackage | OK | - |
| rename-swarm | OK | - |
| skill-creator | OK | - |
| erk-planning (tombstone) | OK | - |

## Fixes

### Fix 1: `refac-mock-to-fake` — CRITICAL

**Problem**: Skill describes a gateway file structure that doesn't exist in erk. It tells agents to create `fake.py` inside gateway directories and references `packages/erk-shared/src/erk_shared/core/fakes.py` which doesn't exist.

**Actual pattern**:
- Gateway dirs contain: `__init__.py`, `abc.py`, `real.py` (+ optional `dry_run.py`/`printing.py`)
- Fakes live in `tests/fakes/gateway/*.py` (e.g., `tests/fakes/gateway/codespace.py`)
- No `fakes.py` in `packages/erk-shared/src/erk_shared/core/`

**File**: `.claude/skills/refac-mock-to-fake/SKILL.md`

**Changes**:
1. **Line 114**: Change `packages/erk-shared/src/erk_shared/gateway/*/fake.py` → `tests/fakes/gateway/*.py`
2. **Line 115-116**: Remove reference to `packages/erk-shared/src/erk_shared/core/fakes.py` (doesn't exist). Replace with `tests/fakes/tests/*.py` for service fakes (FakePromptExecutor, etc.)
3. **Lines 234-240**: Fix "3-file" pattern description from `(abc, real, fake)` to `(abc, real)` with note that fakes go in `tests/fakes/gateway/`. Fix "5-file" pattern similarly — actual 5-file is `(abc, real, dry_run, printing)` plus fake in test dir.
4. **Lines 244-248**: Gateway creation checklist — remove step for creating `fake.py` in gateway dir. Add step for creating fake in `tests/fakes/gateway/<tool_name>.py`

### Fix 2: `fake-driven-testing` — MEDIUM

**Problem**: References nonexistent skill name `dignified-python-313`.

**File**: `.claude/skills/fake-driven-testing/SKILL.md`

**Change**:
- **Line 15**: Change `dignified-python-313` → `dignified-python`

### Fix 3: `ci-iteration` — MEDIUM

**Problem**: References `TodoWrite` tool (doesn't exist in Claude Code). Should reference `TaskCreate`/`TaskUpdate`. Also references `erk sync` which doesn't appear to be a valid command.

**File**: `.claude/skills/ci-iteration/SKILL.md`

**Changes**:
1. **Lines 86, 90, 167**: Replace `TodoWrite` → `TaskCreate/TaskUpdate`
2. **Line 71**: Change `erk sync` → `erk docs sync` (verify exact command name first)
3. **Line 130**: Change `Sync-Kit (erk check)` → `Sync-Kit (erk docs check)` if applicable

### Fix 4: `session-inspector` — HIGH

**Problem**: References files and paths that don't exist.

**File**: `.claude/skills/session-inspector/SKILL.md`

**Changes**:
1. **Line 250**: Remove reference to `extraction.md` from the resources list (file doesn't exist in `references/`)
2. **Lines 257-261**: Fix code dependency paths:
   - `packages/erk-cli/src/erk_cli/commands/` → correct path (erk-cli package doesn't have this structure)
   - `packages/erk-shared/src/erk_shared/extraction/` → remove (directory doesn't exist)
   - Verify remaining paths (`github/metadata.py`, `scratch/`) and update

## Verification

1. Read each modified file after edits to confirm accuracy
2. Cross-reference updated paths with `ls`/`find` to confirm they exist
3. Run `make fast-ci` to ensure no formatting/lint issues in markdown
