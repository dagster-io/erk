# Consolidated Learn Plan: Documentation Updates from 18 Learn Plans

## Source Plans

| # | Title | Category |
|---|-------|----------|
| 9118 | Rename "plan" terminology to "pr" — Phase 1 (Core Types & Gateway) | plan→PR rename |
| 9128 | Rename JSON output fields in exec scripts: plan → pr | plan→PR rename |
| 9139 | Rename Click arguments/options: plan → pr | plan→PR rename |
| 9145 | Update user-facing help strings and error messages: plan → PR | plan→PR rename |
| 9147 | Consolidate workflow dispatch inputs: rename plan_number to pr_number | plan→PR rename |
| 9148 | Update config schema: rename [plans] section to [github] | plan→PR rename |
| 9153 | Simplify plan identification from labels to title prefix | plan→PR rename |
| 9124 | Move test fakes from production packages to tests/fakes/ | testing |
| 9125 | Make `erk reconcile` a hidden command | CLI |
| 9136 | Rename PlanBranchSetup to PlannedBranchSetup | architecture |
| 9137 | Add `erk stack sync` command | CLI/erk |
| 9141 | Push down: Review activity log fetch via new CLI command | CLI |
| 9142 | Hide `learn` command from default CLI help output | CLI |
| 9143 | Optimize Runs Tab Initial Load: parallel batch queries | TUI |
| 9151 | Implement best-of-both-worlds machine command architecture | architecture/CLI |
| 9155 | Consolidate JSON ↔ dataclass utilities into shared module | architecture |
| 9158 | Add cancel and retry commands for workflow runs | CLI |
| 9166 | Create `erk json objective view` and `erk json objective check` machine commands | objectives |

## Phase 1: Update Stale Config Documentation (plan→PR rename)

These files reference the old `[plans]` config section that was renamed to `[github]`.

### Step 1.1: Edit `docs/learned/configuration/config-layers.md`

**Action:** Edit existing file
**Lines to update:**
- Line 51: Change `[plans]` → `[github]`
- Line 75: Change `plans.repo` → `github.repo`
- Add note that `[plans]` is accepted as a backwards-compatible alias

### Step 1.2: Edit `docs/learned/configuration/issues-repo.md`

**Action:** Edit existing file
**Changes:**
- Line 19: Change `[plans]` → `[github]` in TOML example
- Line 28: Change `[plans]` → `[github]` in TOML example
- Line 34: Update "When `plans.repo` is set:" → "When `github.repo` is set:"
- Line 52: Update `plans.repo` reference
- Update frontmatter read-when conditions to reference `github.repo`

### Step 1.3: Edit `docs/learned/planning/cross-repo-plans.md`

**Action:** Edit existing file
**Changes:**
- Line 5: Update frontmatter read-when to reference `[github]`
- Line 24: Change `[plans]` → `[github]` in TOML example
- Line 34: Update "When `[plans] repo` is configured:" → "When `[github] repo` is configured:"

### Step 1.4: Edit `docs/learned/glossary.md`

**Action:** Edit existing file
**Changes:**
- Line 345: Change `[plans]` → `[github]`
- Line 349: Update description referencing `[plans] repo`
- Line 387: Change `plans.repo` → `github.repo`

### Step 1.5: Edit `docs/learned/configuration/index.md`

**Action:** Edit existing file
**Changes:**
- Line 7: Update description for issues-repo.md to reference `github.repo` instead of `plans.repo`

### Step 1.6: Edit `docs/learned/planning/index.md`

**Action:** Edit existing file
**Changes:**
- Line 19: Update description for cross-repo-plans.md to reference `[github]` instead of `[plans]`

## Phase 2: Create New Documentation Files

### Step 2.1: Create `docs/learned/erk/stack-sync.md`

**Action:** Create new file
**Source plans:** #9137
**Content outline:**
```
---
read-when:
  - "working with erk stack sync"
  - "resolving branch divergence across stack"
  - "syncing stack branches with remote"
tripwires: []
---

# Stack Sync Command

## Overview
`erk stack sync` is a hidden command that syncs all branches in the current
Graphite stack with their remote tracking branches.

## Usage
erk stack sync

## Behavior
- Fetches remote state for all branches in the stack
- Resolves divergences via fast-forward or rebase
- Automatic restack after syncing
- Detects conflicts and suggests `erk pr diverge-fix`

## Output Format
- Per-branch results with action label and detail
- Summary statistics: fixed/in-sync/conflicts/skipped

## Implementation
- Location: src/erk/cli/commands/stack/sync_cmd.py
- Hidden command (not shown in `erk --help`)
- Uses GraphiteCommand class
```

**Verification:** Check that `src/erk/cli/commands/stack/sync_cmd.py` matches documented behavior.

### Step 2.2: Create `docs/learned/cli/workflow-run-management.md`

**Action:** Create new file
**Source plans:** #9158
**Content outline:**
```
---
read-when:
  - "canceling or retrying workflow runs"
  - "working with erk workflow run cancel or retry"
  - "managing GitHub Actions workflow runs"
tripwires: []
---

# Workflow Run Management Commands

## Overview
Commands for managing GitHub Actions workflow runs: cancel in-progress
runs and retry failed/completed runs.

## Commands

### erk workflow run cancel <run_id>
Cancel an in-progress or queued workflow run.

### erk workflow run retry <run_id> [--failed]
Retry a completed workflow run.
- `--failed` flag: Only re-run failed jobs (not all jobs)

## Implementation
- Cancel: src/erk/cli/commands/run/cancel_cmd.py
- Retry: src/erk/cli/commands/run/retry_cmd.py
- Both delegate to gh CLI: `gh run cancel` and `gh run rerun`
```

**Verification:** Check command implementations match documented flags and behavior.

### Step 2.3: Create `docs/learned/testing/fakes-directory-structure.md`

**Action:** Create new file
**Source plans:** #9124
**Content outline:**
```
---
read-when:
  - "creating test fakes"
  - "moving fakes from production to test packages"
  - "organizing test doubles"
tripwires:
  - pattern: "creating a fake.*in src/"
    message: "Fakes live in tests/fakes/, not production code"
    doc: "testing/fakes-directory-structure.md"
---

# Test Fakes Directory Structure

## Rule
Test fakes MUST live in `tests/fakes/`, NOT in production packages under `src/`.

## Directory Structure
tests/fakes/
├── __init__.py
├── gateway/
│   ├── __init__.py
│   ├── fake_pr_service.py
│   ├── fake_github_service.py
│   └── ...
└── ...

## Rationale
- Production packages should not contain test infrastructure
- Fakes are test doubles, not production code
- Keeps import boundaries clean
- Prevents accidental production use of fakes

## Migration Pattern
When moving fakes from src/ to tests/fakes/:
1. Create matching directory structure under tests/fakes/
2. Move fake implementation files
3. Update all test imports to reference new locations
4. Remove old fake files from production packages
5. Verify no production code imports fakes
```

**Verification:** Confirm `tests/fakes/` directory structure exists and matches.

### Step 2.4: Create `docs/learned/architecture/json-dataclass-utilities.md`

**Action:** Create new file
**Source plans:** #9155
**Content outline:**
```
---
read-when:
  - "serializing dataclasses to JSON"
  - "parsing JSON into dataclasses"
  - "working with erk_shared JSON utilities"
tripwires: []
---

# JSON ↔ Dataclass Utilities

## Overview
Shared utilities for converting between JSON and frozen dataclasses,
consolidated in the erk_shared package.

## Location
packages/erk-shared/src/erk_shared/json_utils.py (or equivalent)

## Key Utilities
Document the actual functions found in the consolidated module:
- Dataclass to dict conversion
- Dict to dataclass instantiation
- JSON string serialization/deserialization

## Usage Pattern
Import from erk_shared, not from individual packages.

## Rationale
Consolidation eliminated duplicate JSON/dataclass conversion logic
that existed across multiple packages.
```

**Verification:** Find the actual module path in erk_shared and document real function signatures.

### Step 2.5: Create `docs/learned/cli/exec-review-activity-log.md`

**Action:** Create new file
**Source plans:** #9141
**Content outline:**
```
---
read-when:
  - "fetching review activity logs"
  - "working with erk exec get-review-activity-log"
  - "push down review activity log fetch"
tripwires: []
---

# Review Activity Log Fetch (Exec Script)

## Command
erk exec get-review-activity-log --pr-number <N> --marker <marker>

## Purpose
Fetches the activity log section from an existing review summary comment
on a PR. This is a "push down" pattern — moving computation from LLM
prompts into a tested CLI command.

## Output
JSON with:
- found: boolean (whether activity log section was found)
- activity_log: string (the activity log text, or empty)

## Implementation
- Location: src/erk/cli/commands/exec/scripts/get_review_activity_log.py
- Exit code always 0 (supports || true pattern)
```

**Verification:** Check script implementation matches documented output format.

## Phase 3: Update Existing Docs with Stale References

### Step 3.1: Edit `docs/learned/testing/import-conflict-resolution.md`

**Action:** Edit existing file
**Changes:** Update code examples that reference `parse_plan_number` and `plan_helpers` to use current names if they've been renamed. Verify against actual current code before making changes.

### Step 3.2: Edit `docs/learned/cli/workflow-run-list.md`

**Action:** Edit existing file
**Changes:** Line 44 references `extract_plan_number()` — verify this function still exists with this name and update if renamed.

### Step 3.3: Review and update `docs/learned/conventions.md`

**Action:** Edit existing file if needed
**Changes:** Line 32 shows `plan_id` as an example of `_id` suffix convention. This is still valid as a naming convention example (the convention itself hasn't changed, just the domain use). Verify and leave as-is or update example if the field was renamed to `pr_id`.

## Phase 4: Verify No-Op Items (Already Documented)

These plans' content is already captured in existing docs. No action needed, but verify:

- #9151 (machine commands) → Already in `docs/learned/cli/json-command-decorator.md` and `adding-json-to-commands.md`
- #9143 (runs tab optimization) → Already in `docs/learned/tui/runs-tab-architecture.md`
- #9166 (erk json objective commands) → Already in `docs/learned/objectives/objective-view-json.md`
- #9125 (hide reconcile) → Already in `docs/learned/cli/commands/reconcile.md`
- #9142 (hide learn command) → Already in `docs/learned/cli/learn-command-conditional-pipeline.md`
- #9153 (plan identification simplification) → Covered by plan→PR rename docs updates

## Phase 5: Update Index Files

### Step 5.1: Run `erk docs sync` after all changes

**Action:** Run CLI command
**Purpose:** Regenerate auto-generated index files after creating new docs.

## Implementation Notes

- All new files must have frontmatter with `read-when` conditions and `tripwires` (can be empty list)
- Follow existing doc style: short sections, code examples, implementation locations
- Verify all file paths and function names against current codebase before writing
- Do NOT modify CHANGELOG.md