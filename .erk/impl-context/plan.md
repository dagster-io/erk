# Documentation Plan: Remove plan CLI group and relocate duplicate-check to pr group

## Context

This PR represents a significant CLI structure refactoring that removed the top-level `erk plan` command group and relocated its sole remaining command (`duplicate-check`) to the `erk pr` group. The change also removed several deprecated commands: the entire `erk plan docs` subgroup (extract, unextract, unextracted) and `erk plan learn complete`. These commands were part of an older documentation extraction workflow that has been superseded by the current `/erk:learn` pipeline.

This documentation matters because: (1) the command relocation is a user-facing breaking change requiring migration guidance, (2) the removal of deprecated workflows provides important historical context for understanding old plan metadata and GitHub labels, and (3) the PR review process revealed that **stale documentation references persisted after command removal**, highlighting a critical gap in the command removal checklist.

The key non-obvious insight from this implementation is that **documentation references in `docs/learned/` are invisible to type checkers and easy to miss during command removal**. The tripwires bot detected 4 stale references across 3 files that would otherwise have silently misled future agents. This prevention pattern warrants a tripwire addition.

## Raw Materials

PR #8208

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. command-group-structure.md - plan_group references

**Location:** `docs/learned/cli/command-group-structure.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `plan_group` references
**Cleanup Instructions:** Search for references to the removed `plan_group` and update or remove them. The plan group no longer exists; commands have been relocated to `pr` group or removed entirely.

### 2. glossary.md - erk plan learn complete

**Location:** `docs/learned/glossary.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `erk plan learn complete`
**Cleanup Instructions:** Remove or update references to `erk plan learn complete`. This command has been removed. If the glossary entry describes the command's purpose, either remove the entry or update it to note the deprecation and replacement workflow (`/erk:learn` command).

### 3. markers.md - erk plan learn references

**Location:** `docs/learned/architecture/markers.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `erk plan learn` (2 occurrences)
**Cleanup Instructions:** Update references from `erk plan learn` to `erk learn`. The learn command has been promoted from a subcommand under the plan group to a top-level command.

## Documentation Items

### HIGH Priority

#### 1. Update command-organization.md for plan group removal

**Location:** `docs/learned/cli/command-organization.md`
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Updates to existing doc -->

## Changes Required

1. Remove the `### erk plan Subcommands` section references to duplicate-check
2. Add `duplicate-check` to the `### erk pr Subcommands` table:
   | Subcommand        | Description                                  |
   | ----------------- | -------------------------------------------- |
   | `duplicate-check` | Check for duplicate plans before PR creation |

3. Update the "Code Locations" table at the bottom:
   - Change: `| Plan commands     | src/erk/cli/commands/plan/ |`
   - To: Remove row (plan directory no longer exists), ensure duplicate_check_cmd.py is understood to live under pr/

4. In "Adding a New Command" section, update:
   - Change: `- Plan command: src/erk/cli/commands/plan/<name>_cmd.py`
   - To: Remove this line (plan group no longer exists)

5. Update test file references similarly
```

#### 2. Document duplicate-check command relocation

**Location:** `docs/learned/cli/command-organization.md` (add migration note)
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Add to command-organization.md, possibly in a "Migration Notes" section -->

### Command Relocations

#### duplicate-check (PR #8208)

- **Old path:** `erk plan duplicate-check`
- **New path:** `erk pr duplicate-check`
- **Rationale:** The duplicate-check command is primarily used during PR creation workflow, making the `pr` group a more logical home. The plan group was removed as duplicate-check was its sole remaining active command.
- **Migration:** Update any scripts, muscle memory, or documentation referencing the old path.
```

#### 3. Extend command-rename-checklist for group moves

**Location:** `docs/learned/cli/command-rename-checklist.md`
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Add new section after existing content -->

## Cross-Group Moves

When moving a command between groups (e.g., `erk plan duplicate-check` -> `erk pr duplicate-check`), the 9-place checklist applies with these additional considerations:

### Group Registration Changes

Unlike a simple rename within the same group, cross-group moves require:

1. **Remove from old group's `__init__.py`**: Delete the import and `add_command()` registration
2. **Add to new group's `__init__.py`**: Add import and registration to the destination group
3. **Update `cli.py`**: If the old group becomes empty, remove it from the main CLI registration

### Test File Relocation

Test files must move to match the new command location:

- Before: `tests/commands/plan/test_duplicate_check.py`
- After: `tests/commands/pr/test_duplicate_check.py`

### Documentation Updates

Cross-group moves require extra documentation attention:

- `command-organization.md` needs updates to both the source and destination group tables
- Help text examples showing the command path must be updated
- Error messages referencing the old path must be updated

### Example: PR #8208

The `duplicate-check` command moved from `plan` to `pr`:

- Old registration: `src/erk/cli/commands/plan/__init__.py`
- New registration: `src/erk/cli/commands/pr/__init__.py`
- Test moved: `tests/commands/plan/` -> `tests/commands/pr/`
- Plan group removed (became empty)
```

#### 4. Add stale documentation reference scanning to incomplete-command-removal.md

**Location:** `docs/learned/cli/incomplete-command-removal.md`
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Add to the "4-Step Prevention Pattern" section, making it 5 steps -->

## 5-Step Prevention Pattern

Before removing any command or workflow:

1. **Search string references**: `grep -r "command-name" src/ tests/ .github/ .claude/`
2. **Search WORKFLOW_COMMAND_MAP**: Check `src/erk/cli/constants.py` for the command key
3. **Search workflow files**: Check `.github/workflows/` for matching YAML
4. **Search documentation**: Check `docs/learned/` and `.claude/commands/` for references
5. **Search learned docs thoroughly**: Run `grep -r "command-name" docs/learned/` to catch:
   - Glossary entries
   - Architecture docs with command examples
   - Tripwire docs referencing the command
   - Any doc mentioning the command path

### Why Step 5 Matters (PR #8208)

The tripwires bot detected 4 stale references that Step 4's broader search missed:
- `docs/learned/cli/command-group-structure.md` - `plan_group` references
- `docs/learned/glossary.md` - `erk plan learn complete` entry
- `docs/learned/architecture/markers.md` - 2 references to `erk plan learn`

These references would have silently misled future agents. The dedicated `docs/learned/` grep in Step 5 ensures comprehensive coverage.
```

### MEDIUM Priority

#### 5. Document docs extraction workflow removal

**Location:** `docs/learned/planning/docs-extraction-workflow-removal.md`
**Action:** CREATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
---
title: Docs Extraction Workflow Removal
read_when:
  - "encountering docs-extracted GitHub label on old plans"
  - "understanding historical plan metadata"
  - "researching removed erk plan docs commands"
---

# Docs Extraction Workflow Removal

The `erk plan docs` command group was removed in PR #8208. This document provides historical context.

## Removed Commands

- `erk plan docs extract <issue>` - Mark a plan as having its session logs analyzed
- `erk plan docs unextract <issue>` - Remove the docs-extracted label
- `erk plan docs unextracted` - List plans without the docs-extracted label

## GitHub Label

The workflow used a `docs-extracted` GitHub label (purple, description: "Session logs analyzed for documentation improvements") to track which plans had been reviewed for documentation opportunities.

## Why Removed

The workflow was superseded by the `/erk:learn` pipeline, which:
- Automatically processes session logs when a plan lands
- Does not require manual label management
- Integrates with the `erk-learn` plan type for tracking

## Migration

No migration needed. The label may still exist on historical issues. New plans use the `erk-learn` plan type and `/erk:learn` command.

<!-- Source: Deleted files in src/erk/cli/commands/plan/docs/ and src/erk/cli/constants.py (DOCS_EXTRACTED_LABEL) -->
```

#### 6. Document learn complete command deprecation

**Location:** `docs/learned/planning/learn-complete-deprecation.md`
**Action:** CREATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
---
title: Learn Complete Command Deprecation
read_when:
  - "encountering source_plan_issues field in old plan metadata"
  - "researching removed erk plan learn complete command"
---

# Learn Complete Command Deprecation

The `erk plan learn complete` command was removed in PR #8208.

## What It Did

The command was intended to mark source plans as "docs-extracted" after a learn plan completed. It operated on the `source_plan_issues` metadata field, which tracked which plans had been analyzed for documentation.

## Why Removed

The `source_plan_issues` schema field was removed from the plan metadata schema. The learn workflow evolved to:
- Track learning via plan associations (learn plans reference their source plans)
- Use the `/erk:learn` command directly without intermediate marking steps

## Historical Context

Learn plans previously maintained a list of source plans they analyzed. The `complete` command would iterate through this list and apply the `docs-extracted` label to each. This was manual overhead that the current automated pipeline eliminates.

<!-- Source: Deleted file src/erk/cli/commands/plan/learn/complete_cmd.py -->
```

#### 7. Update navigation_helpers error message documentation

**Location:** `docs/learned/cli/command-organization.md` (or create error-messages.md if none exists)
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Add note about the error message simplification -->

### Command Path Simplification

Error messages have been updated to reflect simplified command paths:

- **Before:** "Run: erk plan learn raw"
- **After:** "Run: erk learn"

This change appears in `check_pending_learn_marker()` in `src/erk/cli/commands/navigation_helpers.py`. The learn command was promoted to a top-level command, and error messages should direct users to the current path.

When updating command paths in error messages, ensure:
1. The message uses the current command path
2. Related test assertions are updated (e.g., `tests/commands/workspace/test_delete.py`)
```

### LOW Priority

#### 8. Document CLI group consolidation decision framework

**Location:** `docs/learned/cli/command-organization.md` (add to Decision Framework section)
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Add to Decision Framework section -->

### When to Remove a Top-Level Group

Consider removing a top-level command group when:

1. **Single remaining command**: The group has only one active command
2. **Better fit elsewhere**: That command has a more natural home in another group
3. **Low discovery value**: The group name doesn't aid command discovery

**Example: Plan Group Removal (PR #8208)**

The `plan` group was removed because:
- Its sole active command (`duplicate-check`) fit better under `pr` (used during PR creation)
- Other plan commands (`docs`, `learn complete`) were deprecated
- High-frequency plan operations (`implement`, `prepare`, `dash`) were already top-level

**Anti-pattern: Premature Group Creation**

Avoid creating top-level groups for domain areas that overlap with existing groups. If a command primarily supports an existing workflow (like PR creation), place it under that workflow's group rather than creating a new parallel hierarchy.
```

#### 9. Document DOCS_EXTRACTED_LABEL removal

**Location:** `docs/learned/planning/docs-extraction-workflow-removal.md` (consolidate with item 5)
**Action:** CREATE (consolidated)
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- This content is consolidated into the docs-extraction-workflow-removal.md draft above -->
<!-- The DOCS_EXTRACTED_LABEL constants section documents: -->

## Removed Constants

The following constants were removed from `src/erk/cli/constants.py`:

- `DOCS_EXTRACTED_LABEL = "docs-extracted"` - The GitHub label name
- `DOCS_EXTRACTED_LABEL_DESCRIPTION = "Session logs analyzed for documentation improvements"` - Label description
- `DOCS_EXTRACTED_LABEL_COLOR = "5319E7"` - Purple color code

These constants were only used by the now-removed `erk plan docs` commands.
```

#### 10. Document test organization pattern for feature removal

**Location:** `docs/learned/testing/testing.md` (add note about test cleanup)
**Action:** UPDATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
<!-- Add to existing testing documentation -->

## Test Cleanup During Feature Removal

When removing a feature or command, ensure comprehensive test cleanup:

1. **Delete test files**: Remove test files that test the removed feature
2. **Mirror directory structure**: Test directories should mirror source structure
   - Source: `src/erk/cli/commands/plan/docs/` -> Tests: `tests/commands/plan/docs/`
3. **Update import paths**: Tests importing from removed modules need updates or deletion
4. **Update assertions**: Tests asserting on removed behavior (error messages, command output) need updates

**Example: PR #8208**

Removed test directories:
- `tests/commands/plan/docs/` (336 lines of test coverage)
- `tests/commands/plan/learn/` (124 lines of test coverage)

Updated test files:
- `tests/commands/workspace/test_delete.py` - Updated error message assertion from "erk plan learn raw" to "erk learn"
```

#### 11. Document learn workflow evolution

**Location:** `docs/learned/planning/learn-workflow-evolution.md`
**Action:** CREATE
**Source:** [PR #8208]

**Draft Content:**

```markdown
---
title: Learn Workflow Evolution
read_when:
  - "understanding how the learn workflow changed over time"
  - "encountering old plan metadata with docs-related fields"
---

# Learn Workflow Evolution

The documentation learning workflow has evolved significantly. This document traces the changes.

## Historical Workflow (Pre-PR #8208)

1. Implement a plan
2. Run `erk plan docs unextracted` to find plans without documentation review
3. Manually run documentation extraction
4. Run `erk plan docs extract <issue>` to mark as processed
5. After learn plan completion, run `erk plan learn complete` to mark source plans

## Current Workflow (Post-PR #8208)

1. Implement a plan
2. Run `/erk:learn` command (or let CI trigger it automatically)
3. Learn pipeline processes session logs and creates documentation updates
4. No manual label management required

## Key Changes

| Aspect | Historical | Current |
|--------|-----------|---------|
| Tracking mechanism | `docs-extracted` GitHub label | `erk-learn` plan type |
| Command location | `erk plan docs/*`, `erk plan learn complete` | `/erk:learn` slash command |
| Automation | Manual | CI-triggered via `trigger-async-learn` |
| Source plan tracking | `source_plan_issues` metadata field | Plan associations |

## Migration Notes

- The `docs-extracted` label may still exist on historical issues
- Old plan metadata may contain `source_plan_issues` field (no longer used)
- `/erk:learn` is the current entry point for all documentation learning

<!-- Source: PR #8208 removed erk plan docs/* and erk plan learn complete commands -->
```

## Contradiction Resolutions

No contradictions found. The existing documentation in `docs/learned/cli/command-organization.md` describes command placement philosophy that is consistent with this refactoring. Moving `duplicate-check` from `erk plan` to `erk pr` aligns with the documented principle that PR-related operations belong under the `pr` group.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Stale Documentation References After Command Removal

**What happened:** After removing the `erk plan` group and its subcommands, the tripwires bot detected 4 stale references across 3 documentation files that still mentioned the removed commands.

**Root cause:** The existing "4-Step Prevention Pattern" in `incomplete-command-removal.md` included a general "search documentation" step, but it was not specific enough. Developers searched `.claude/commands/` but did not thoroughly grep `docs/learned/` for all variations of the command names.

**Prevention:** Add explicit Step 5 to the prevention pattern: "Search learned docs thoroughly" with a dedicated `grep -r "command-name" docs/learned/` command. This catches glossary entries, architecture docs with examples, and tripwire docs referencing the command.

**Recommendation:** TRIPWIRE - This pattern is non-obvious, cross-cutting (applies to all command removals), and causes silent failures (stale references don't break builds but mislead future developers).

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Stale documentation references after command removal

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before removing a CLI command or group
**Warning:** "Search docs/learned/ for all references to the command name (both full path and short name). Update or remove references in: command lists, examples, glossary entries, error message documentation, and architectural docs. Run: `grep -r 'command-name' docs/learned/`"
**Target doc:** `docs/learned/cli/tripwires.md`

This tripwire is warranted because documentation references are invisible to static analysis tools. The tripwires bot caught 4 references that would have silently persisted, misleading future agents with outdated command paths. The prevention is simple (a grep command) but non-obvious during the pressure of feature removal. Adding this as a tripwire in the CLI tripwires file ensures agents see the warning before any command removal operation.

The existing `incomplete-command-removal.md` doc already has a tripwire entry, but it should be enhanced to specifically call out the `docs/learned/` search as a distinct, mandatory step.

## Potential Tripwires

No items with borderline scores (2-3) were identified. The stale documentation reference pattern scored 6, well above the threshold.
