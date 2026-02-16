# Documentation Plan: Audit Top 7 High-Priority docs/learned/ Documents

## Context

This documentation plan synthesizes learnings from 10 implementation sessions that audited 7 high-priority docs/learned/ documents (score 11-12). The sessions revealed significant patterns around testing workflows, PR operations, documentation audit methodology, and architectural decisions that benefit future agents.

The primary implementation (PR #7134) audited documentation files, applying source pointer conversions, updating stale skill registration patterns (from individual capability files to bundled_skills() dict), and expanding hooks documentation (10 to 14 lifecycle events, 2 to 3 hook types). Beyond the audit itself, the sessions uncovered critical workflow patterns: parameter injection testing strategies, false positive detection in automated reviews, and when to skip plan mode for pre-planned tasks.

Future agents working with erk will benefit from documentation on: (1) HIGH-severity prevention insights around test scope discovery and import patching, (2) the distinction between test factory defaults and production code standards, (3) audit protocols for auto-generated files, and (4) batch operation thresholds that dramatically improve efficiency.

## Raw Materials

https://gist.github.com/schrockn/20aaeb6ebebc3aed0e0d74c85168aee5

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 19    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 6     |
| Potential tripwires (score2-3) | 8     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Hooks Documentation Path Reference

**Location:** `docs/learned/hooks/hooks.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/exec/pre_tool_use_hook.py` (actual: `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py`)
**Cleanup Instructions:** Update the hook script path reference to reflect the directory restructuring. Core content (hooks lifecycle, matchers) remains valid.

## Documentation Items

### HIGH Priority

#### 1. False Positive Detection Workflow

**Location:** `docs/learned/pr-operations/false-positive-detection.md`
**Action:** CREATE
**Source:** [Impl] Sessions 63468c43, fd276831

**Draft Content:**

```markdown
---
description: Workflow for identifying and handling automated reviewer false positives
read_when:
  - handling automated review bot comments
  - dignified-code-simplifier or linter flags code
  - review comment references code already changed in PR
---

# False Positive Detection in Automated Reviews

## Overview

Automated review bots (dignified-code-simplifier, linters) may flag code patterns that are either already fixed in the PR or intentionally designed that way (e.g., test factory functions).

## Detection Workflow

1. **Read the flagged code** at its current state in the PR
2. **Check the PR diff** using `gh pr diff` to see what changes the PR already makes
3. **Verify the complaint is valid** - does the issue exist in current state?
4. **Check context** - is this a test factory function where defaults are intentional?
5. **If false positive**: Resolve thread with explanation, no code change needed

## Common False Positive Patterns

### Already Fixed in PR

The bot may reference a diff line number where the fix already exists. The bot flagged its own fix.

**Resolution**: Resolve thread explaining the issue is already addressed in the PR's changes.

### Test Factory Functions

Functions named `make_*` or `create_*` in test code are designed with defaults for ergonomic test creation. The "no default parameters" rule applies to production code, not test factories.

See `make_plan_row()` in `tests/unit/tui/providers/test_provider.py` for example - five parameters use defaults by design.

**Resolution**: Resolve as false positive, citing that test factory functions are exempt.

## Tripwires

- Before making code changes based on automated reviewers, read the full function context
- If bot flags parameter in `make_*` or `create_*` function, verify it's not a test factory
```

---

#### 2. Parameter Injection Testing Pattern

**Location:** `docs/learned/testing/parameter-injection-pattern.md`
**Action:** CREATE
**Source:** [Impl] Session c0f0f858

**Draft Content:**

```markdown
---
description: Converting tests from monkeypatch to parameter injection for testability
read_when:
  - adding parameters to functions for testability
  - refactoring functions to accept dependencies as parameters
  - encountering monkeypatch AttributeError after import removal
---

# Parameter Injection Testing Pattern

## Overview

When adding parameters to functions to improve testability, tests must be updated to use parameter injection rather than monkeypatching. This pattern is more explicit and less brittle than patching module imports.

## Two-Phase Refactoring Strategy

### Phase 1: Direct Callers

Tests that call the function directly should pass parameters explicitly.

See `test_orphans.py` and `test_missing.py` in `tests/unit/artifacts/` for examples - these tests pass `bundled_claude_dir` and `bundled_skills_dir` directly to `find_orphaned_artifacts()` and `find_missing_artifacts()`.

### Phase 2: CLI Tests

Tests that invoke functions through CLI commands cannot pass parameters directly (the CLI calls internal functions). These tests legitimately need monkeypatching, but patches must target the correct import location.

**Critical**: Patches target the import location (call site), not the definition site.

See `test_cli.py` patching `erk.cli.commands.artifact.check.get_bundled_claude_dir` (import location) not `erk.artifacts.artifact_health.get_bundled_claude_dir` (definition).

## Scope Discovery Before Implementation

Before changing function signatures:

1. Grep ALL call sites: `grep "function_name\(" src/ tests/`
2. Identify which tests call directly vs through CLI
3. Create a complete list of files needing updates
4. Plan Phase 1 and Phase 2 updates separately

## Prevention Insights

**Monkeypatch AttributeError**: Removing imports from a module while tests still patch that location causes AttributeError. Before removing imports, grep ALL test files for monkeypatch statements targeting the module.

## Tripwires

- HIGH: Before adding required parameters, grep ALL call sites and convert direct callers to parameter injection
- HIGH: Before removing imports, grep test files for monkeypatch statements targeting that module
```

---

#### 3. Test Helper Default Value Anti-Pattern

**Location:** `docs/learned/testing/test-helper-defaults.md`
**Action:** CREATE
**Source:** [Impl] Session 3aebf0ef

**Draft Content:**

```markdown
---
description: Avoiding test helper defaults that overlap with test data queries
read_when:
  - adding defaults to test helper functions
  - test failures after adding new filterable fields
  - query matching multiple fields unexpectedly
---

# Test Helper Default Values

## The Anti-Pattern

Test helper defaults should not overlap with common test queries.

**Bad**: `make_plan_row(author="test-user")` - querying "user" now matches both title and author fields

**Good**: `make_plan_row(author="helper-default-author")` - distinct value won't accidentally match test data

## Why This Matters

When adding a new filterable field (like author), existing tests may break:
1. Test queries "user" expecting to match title "Add USER Authentication"
2. After adding author field with default "test-user", query matches both
3. Test expects 1 result, gets 2

## Prevention

When adding defaults to test helpers:
1. Check existing test data patterns in the test file
2. Verify default won't overlap with common test queries
3. Use fully distinct values that describe their purpose

## Example

See `make_plan_row()` in `tests/unit/tui/providers/test_provider.py` - the `author` default should be distinguishable from any title content used in tests.

## Tripwires

- When adding defaults to test helpers, verify they don't overlap with existing test data patterns
```

---

#### 4. Plan Mode vs Direct Execution

**Location:** `docs/learned/planning/when-to-skip-planning.md`
**Action:** CREATE
**Source:** [Impl] Session b33fe8cb

**Draft Content:**

```markdown
---
description: When to skip plan creation and execute directly
read_when:
  - considering entering plan mode
  - user rejected ExitPlanMode tool use
  - command provides explicit step-by-step instructions
---

# When to Skip Plan Mode

## The Pattern

Don't enter plan mode when explicit step-by-step instructions already exist.

Commands like `/erk:fix-conflicts` provide comprehensive instructions:
1. Read conflicted files
2. Analyze conflict type
3. Execute resolution strategy
4. Continue rebase

Creating a plan file adds overhead without value - the task is already decomposed.

## Heuristics

**Skip planning when:**
- Command documentation provides numbered steps
- User's prompt contains explicit instructions
- Task is mechanical execution of known steps

**Use planning when:**
- Task requires research or discovery
- Multiple approaches need evaluation
- Scope is unclear and needs decomposition

## Prevention

Before entering plan mode:
1. Check if current command provides step-by-step instructions
2. Check if user's prompt already decomposes the task
3. If yes to either: skip planning, proceed to execution

## Related

The analysis phase (reading files, understanding conflicts) remains valuable. Only the formalization into a plan document is redundant when instructions exist.

## Tripwires

- Before entering plan mode, check if task has explicit step-by-step instructions
```

---

#### 5. Auto-Generated File Audit Protocol

**Location:** `docs/learned/documentation/audit-auto-generated-files.md`
**Action:** CREATE
**Source:** [Impl] Session ebd45ec4

**Draft Content:**

```markdown
---
description: Audit protocol for files with AUTO-GENERATED FILE comment
read_when:
  - auditing docs/learned/ files
  - file contains AUTO-GENERATED FILE comment
  - considering edits to tripwires.md files
---

# Auto-Generated File Audit Protocol

## Detection

Files with `<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->` are generated by `erk docs sync` from source documents.

## STAMP ONLY Approach

For auto-generated files:

1. **Add audit metadata** to frontmatter (will be overwritten, but creates audit trail)
2. **Do NOT edit content** - changes will be lost on next `erk docs sync`
3. **Focus verification on source docs** that feed the generation
4. **Verify generation is working** by checking output matches source

## Common Auto-Generated Files

- `docs/learned/*/tripwires.md` - generated from frontmatter in category docs
- `docs/learned/index.md` - generated from all category indexes

## After Auditing

Run `erk docs sync` to regenerate auto-generated files with any source changes.

## Tripwires

- Before editing files with `<!-- AUTO-GENERATED FILE -->`, apply STAMP ONLY approach
```

---

### MEDIUM Priority

#### 6. Filter Extension Pattern

**Location:** `docs/learned/tui/filter-extension-pattern.md`
**Action:** CREATE
**Source:** [Impl] Session 3aebf0ef

**Draft Content:**

```markdown
---
description: Four-step pattern for adding a filterable field to TUI
read_when:
  - adding a new filterable field to erk dash
  - extending filter_plans() function
  - search filter needs to match additional fields
---

# Filter Extension Pattern

## The Four Steps

When adding a new filterable field:

### 1. Add field to dataclass

Add the field to `PlanRowData` dataclass.

See `PlanRowData.author` field in `src/erk/tui/providers/provider.py`.

### 2. Thread through data pipeline

Extract from source (`IssueInfo`) and pass as parameter to `_build_row_data()`.

See `RealPlanDataProvider._build_row_data()` which receives `author` parameter.

### 3. Add filter logic

Add case-insensitive matching in `filter_plans()`.

See author matching logic in `filter_plans()` in `src/erk/tui/providers/filter.py`.

### 4. Update tests

- Add parameter to test helper with distinct default
- Update tests that might now match multiple fields
- Test both inclusion (field matches) and exclusion (field doesn't match)

## Provider-Agnostic vs Provider-Specific

**Provider-agnostic** (add to Plan dataclass): Data all providers can supply
**Provider-specific** (pass as parameter): Data only GitHub provider has (like `issue.author`)

See architectural decision in `_build_row_data()` parameter design.
```

---

#### 7. Provider-Agnostic vs Provider-Specific Data

**Location:** `docs/learned/architecture/plan-data-provider-design.md`
**Action:** CREATE
**Source:** [Impl] Session 3aebf0ef

**Draft Content:**

```markdown
---
description: When to add fields to Plan vs pass as parameters to _build_row_data()
read_when:
  - adding new fields to TUI data pipeline
  - deciding where data belongs in Plan architecture
  - working with PlanRowData and RealPlanDataProvider
---

# Plan Data Provider Design

## The Decision

When adding data to the TUI:

### Add to Plan dataclass

Data that ALL providers could supply, regardless of data source.

Examples: plan title, status, timestamps, file paths

### Pass as parameter to _build_row_data()

Data that is provider-specific (only available from certain sources).

Examples: `issue.author` from GitHub, file modification time from local files

## Rationale

The `Plan` type is provider-agnostic - it should work whether plans come from GitHub issues, local files, or other sources. Provider-specific data like GitHub issue author should be passed as parameters.

## Example

See `author` parameter in `RealPlanDataProvider._build_row_data()` - extracted from `IssueInfo.author` and passed through rather than added to the `Plan` dataclass.
```

---

#### 8. Source Pointer Conversion Workflow

**Location:** `docs/learned/documentation/source-pointer-workflow.md`
**Action:** CREATE
**Source:** [Impl] Session 0b90ce8a

**Draft Content:**

```markdown
---
description: Pattern for converting code blocks to source pointers in documentation
read_when:
  - converting verbatim code to source pointers
  - reducing code duplication in docs
  - auditing docs with large code blocks
---

# Source Pointer Conversion Workflow

## Overview

Convert verbatim code blocks to two-part source pointers to prevent documentation staleness.

## The Two-Part Format

1. **HTML comment**: Points to exact location for grep-ability
2. **Prose reference**: Human-readable description of what to find

Example:
```html
<!-- Source: bundled_skills() in src/erk/capabilities/bundled.py -->
```

"Add a new entry to the `bundled_skills()` dict, mapping the skill name to its BundledSkillCapability instance."

## Conversion Steps

1. Read `docs/learned/documentation/source-pointers.md` for format details
2. Identify code block to convert
3. Locate the source in codebase
4. Write HTML comment with file path and function/class name
5. Write prose description conveying the same information
6. Remove verbatim code block

## When to Keep Code

Short illustrative snippets (<=5 lines) showing a pattern are acceptable. Replace large blocks (>5 lines) with source pointers.

## Prose Reference Examples

**Dict registration**: "Add a new entry mapping the name to its capability instance"
**Factory call**: "The factory method handles instantiation and registration"
**Config pattern**: "Follow the existing entries in the config dict"
```

---

#### 9. Batch Thread Resolution

**Location:** `docs/learned/pr-operations/batch-thread-resolution.md`
**Action:** UPDATE (add to existing PR operations docs)
**Source:** [Impl] Sessions 0b90ce8a, 63468c43

**Draft Content:**

```markdown
## Batch Thread Resolution

Resolve multiple review threads in a single API call using `erk exec resolve-review-threads`.

### JSON Stdin Format

```json
[
  {
    "thread_id": "<thread-id>",
    "body": "Explanation for resolution"
  },
  {
    "thread_id": "<thread-id-2>",
    "body": "Second explanation"
  }
]
```

### Usage

```bash
echo '[{"thread_id": "123", "body": "Fixed"}]' | erk exec resolve-review-threads --pr 7134
```

### When to Use

- Multiple threads can be resolved together (same batch)
- More efficient than individual `resolve-review-thread` calls
- Especially useful after batch code fixes

See `erk exec resolve-review-threads` command implementation for details.
```

---

#### 10. Batch File Editing Threshold

**Location:** `docs/learned/workflows/batch-file-editing.md`
**Action:** CREATE
**Source:** [Impl] Session e8f63d16

**Draft Content:**

```markdown
---
description: When to use sed/Bash for bulk file changes vs Edit tool
read_when:
  - more than 30 files need identical changes
  - mechanical find-replace across many files
  - batch format updates
---

# Batch File Editing Threshold

## The Rule

When **>30 files** need identical mechanical changes, delegate to Bash subagent with sed/awk/find.

## Why

- 122 files via sed: ~21 seconds
- 122 files via Edit tool: ~122 individual tool calls, several minutes, clutters conversation

## Pattern

```bash
# Example: Update date format in all markdown files
find docs/learned -name "*.md" -exec sed -i 's/YYYY-MM-DD$/YYYY-MM-DD HH:MM PT/g' {} +
```

## Verification

After bulk edits, always verify:

1. Zero matches for old pattern: `grep -r "old_pattern" docs/`
2. Expected matches for new pattern: `grep -r "new_pattern" docs/ | wc -l`

## Threshold Justification

- <10 files: Edit tool is fine
- 10-30 files: Edit tool acceptable, sed optional
- >30 files: sed strongly preferred for efficiency

See `_validate_last_audited_format()` migration in `src/erk/agent_docs/operations.py` for example.
```

---

#### 11. Validation Layer Placement

**Location:** `docs/learned/architecture/validation-layer-placement.md`
**Action:** CREATE
**Source:** [Impl] Session e8f63d16

**Draft Content:**

```markdown
---
description: Where different types of validation belong in the codebase
read_when:
  - adding format validation
  - deciding where to enforce constraints
  - validation logic placement
---

# Validation Layer Placement

## Principle

Validation belongs at the **data layer** (operations modules), not at command or presentation layers.

## Why

Data layer validation ensures all code paths enforce constraints, regardless of entry point (CLI, API, programmatic).

## Example

`LAST_AUDITED_PATTERN` validation in `src/erk/agent_docs/operations.py` - validates format in `validate_agent_doc_frontmatter()`, not in CLI commands.

## Layer Responsibilities

- **Data layer** (operations.py): Format validation, constraint enforcement
- **Command layer** (CLI): User input parsing, error display
- **Presentation layer** (TUI): Display formatting, user interaction

## Anti-Pattern

Validating in CLI command and forgetting the constraint when data is modified programmatically.
```

---

#### 12. Sentinel Values in Migrations

**Location:** `docs/learned/conventions.md` (add section)
**Action:** UPDATE
**Source:** [Impl] Session e8f63d16

**Draft Content:**

```markdown
## Sentinel Values in Migrations

When migrating from partial to complete data format, use distinguishable sentinel values.

### Example

Migrating `last_audited` from date-only to datetime:
- Old format: `2025-02-15`
- New format: `2025-02-15 14:30 PT`
- Migration sentinel: `2025-02-15 00:00 PT`

The `00:00 PT` sentinel distinguishes "migrated from old format" from "explicitly audited at midnight".

### Pattern

Choose sentinel values that:
1. Are valid in the new format
2. Are distinguishable from realistic values
3. Convey the migration status
```

---

#### 13. Rebase Conflict Resolution Strategy

**Location:** `docs/learned/workflows/rebase-conflict-resolution.md`
**Action:** CREATE
**Source:** [Impl] Sessions 160c3738, b33fe8cb

**Draft Content:**

```markdown
---
description: When to use git checkout --ours vs manual resolution in rebases
read_when:
  - resolving rebase conflicts
  - branch conflicts with merged PR
  - choosing between conflicting implementations
---

# Rebase Conflict Resolution Strategy

## Merged PR Precedence

When rebasing and conflicts occur with an already-merged PR:

**Take HEAD (`git checkout --ours`)** - the merged code has passed review.

## Heuristics

### Take HEAD when:
- Base contains merged, reviewed implementation
- HEAD uses erk conventions (LBYL over EAFP)
- HEAD preserves format, branch forces conversion

### Manual resolution when:
- Both implementations have unique value
- Downstream commits depend on branch's approach
- Semantic differences require careful merging

## Auto-Drop Detection

Git detects "already upstream" commits and auto-drops them during rebase. This is expected when rebasing after dependent PR merges.

## Example

See conflict resolution in session 160c3738 - LBYL implementation (HEAD) preferred over EAFP (branch) per erk conventions.

## Tripwires

- When rebase conflicts with merged PR, prefer HEAD's reviewed implementation
```

---

#### 14. Two-Phase Test Refactoring

**Location:** `docs/learned/testing/signature-change-test-updates.md`
**Action:** CREATE
**Source:** [Impl] Session c0f0f858

**Draft Content:**

```markdown
---
description: Strategy for updating tests when changing function signatures
read_when:
  - adding parameters to functions
  - refactoring function signatures
  - test failures after signature changes
---

# Two-Phase Test Refactoring Strategy

## Overview

When changing function signatures, tests require different treatment based on how they call the function.

## Phase 1: Direct Callers

Tests that call the function directly → convert to parameter injection.

```python
# Before: monkeypatch
mocker.patch("erk.artifacts.artifact_health.get_bundled_claude_dir")

# After: parameter injection
find_orphaned_artifacts(bundled_claude_dir=tmp_path / ".claude")
```

## Phase 2: CLI/Integration Tests

Tests that invoke through CLI → retarget patches to import location.

```python
# Patch where function is IMPORTED (call site)
mocker.patch("erk.cli.commands.artifact.check.get_bundled_claude_dir")

# NOT where it's DEFINED (source)
mocker.patch("erk.artifacts.artifact_health.get_bundled_claude_dir")  # WRONG
```

## Scope Discovery

Before implementation:
1. `grep "function_name\(" src/ tests/` - find all callers
2. Categorize: direct calls vs CLI/integration
3. Plan Phase 1 and Phase 2 updates separately

## Tripwires

- HIGH: Grep ALL call sites before changing signatures
- HIGH: Convert direct callers to injection, retarget CLI test patches
```

---

### LOW Priority

#### 15. Illustrative Path Validation

**Location:** `docs/learned/documentation/audit-methodology.md` (add section)
**Action:** UPDATE
**Source:** [Impl] Session ebd45ec4

**Draft Content:**

```markdown
## Illustrative Path Validation

When auditing docs, distinguish broken references from illustrative examples.

### Broken Reference
Path in prose that should exist but doesn't: "See `src/erk/capabilities/skills/dignified_python.py`"

### Illustrative Example
Path in code template showing a pattern: `packages/erk-shared/src/erk_shared/gateway/command_executor.py` in a transformer template

### Classification

Check context:
- **Prose reference**: Should be verified against filesystem
- **Code template/example**: Teaching pattern, not reference to existing file
- **Comment showing format**: Illustrative, not reference

Don't flag illustrative paths as broken references.
```

---

#### 16. Line Number Reference Removal

**Location:** `docs/learned/documentation/source-pointers.md` (add section)
**Action:** UPDATE
**Source:** [Impl] Session ebd45ec4

**Draft Content:**

```markdown
## Line Number References

### When to Remove

**Prose line references**: `see line 578` → remove, use function name instead

Line numbers drift with every edit. Function names are stable anchors.

### When to Keep

**Source pointer comments**: Keep for grep-ability if code is stable and function is unique.

### Conversion Examples

- `list_cmd.py:578-629` → `_run_watch_loop() in list_cmd.py`
- `submit.py:151-153` → `_prompt_existing_branch_action() in submit.py`
```

---

#### 17. Progressive Verification Strategy

**Location:** `docs/learned/documentation/audit-methodology.md` (add section)
**Action:** UPDATE
**Source:** [Impl] Session ebd45ec4

**Draft Content:**

```markdown
## Progressive Verification Strategy

When auditing docs, verify progressively:

1. **File exists**: `ls <path>` to check referenced files exist
2. **Contents match**: Read file to verify claims about contents
3. **Behavioral claims accurate**: Test or trace to verify runtime behavior
4. **Third-party source check**: For reference caches, fetch authoritative docs

Don't assume from doc content alone. Verify each level before proceeding.
```

---

#### 18. Test Factory Function Exemption

**Location:** `docs/learned/testing/test-factory-exemptions.md`
**Action:** CREATE
**Source:** [Impl] Session fd276831

**Draft Content:**

```markdown
---
description: Test factory functions are exempt from production code rules
read_when:
  - bot flags default in make_* or create_* function
  - applying coding standards to test helpers
---

# Test Factory Function Exemptions

## The Rule

Test factory functions (functions whose purpose is creating test data with sensible defaults) are exempt from the "no default parameter values" rule.

## Identification

Functions named `make_*` or `create_*` in test code that exist to provide convenient test data creation.

## Example

`make_plan_row()` in `tests/unit/tui/providers/test_provider.py` uses defaults for all parameters - this is intentional design for test ergonomics.

## When Bots Flag

If dignified-code-simplifier flags a default in a test factory:
1. Check if function is named `make_*` or `create_*`
2. Check if nearby parameters also use defaults
3. If yes: resolve as false positive, test factories use defaults by design
```

---

#### 19. Import Location for Test Patches

**Location:** `docs/learned/testing/import-location-patching.md`
**Action:** CREATE
**Source:** [Impl] Session c0f0f858

**Draft Content:**

```markdown
---
description: Patches must target import location, not definition site
read_when:
  - test patches failing after module refactoring
  - AttributeError in monkeypatch statements
  - function moved between modules
---

# Import Location for Test Patches

## The Rule

When patching functions in tests, target the **import location** (where the function is called), not the **definition site** (where the function is defined).

## Example

Function `get_bundled_claude_dir()` defined in `erk.artifacts.artifact_health` but imported and called in `erk.cli.commands.artifact.check`:

```python
# CORRECT - patch at import location
mocker.patch("erk.cli.commands.artifact.check.get_bundled_claude_dir")

# WRONG - patch at definition site
mocker.patch("erk.artifacts.artifact_health.get_bundled_claude_dir")
```

## Why

Python's import system binds names at import time. The call site uses its local binding, not the original module's.

## When Functions Move

After refactoring:
1. Find where function is now imported
2. Update patches to target new import location
3. Or convert to parameter injection (preferred)
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Monkeypatch AttributeError after Import Removal

**What happened:** Removed import from `artifact_health.py` but tests still monkeypatched that location, causing AttributeError.
**Root cause:** Import removal without updating test patch targets.
**Prevention:** Before removing imports, grep ALL test files for monkeypatch statements targeting that module.
**Recommendation:** TRIPWIRE (score 7)

### 2. Incomplete Scope Discovery

**What happened:** Started implementation without identifying all affected test files, leading to multiple rounds of fixes.
**Root cause:** Missing comprehensive grep before changing signatures.
**Prevention:** Use `grep "function_name\(" src/ tests/` to find ALL uses before making changes.
**Recommendation:** TRIPWIRE (score 7)

### 3. Test Failures Attributed to Wrong Cause

**What happened:** Assumed test failures were caused by current refactoring, wasted time debugging.
**Root cause:** Two tests were already broken on master.
**Prevention:** Use `git stash && pytest <test> && git stash pop` to verify tests pass on clean master.
**Recommendation:** ADD_TO_DOC

### 4. Missing the Objective of Refactoring

**What happened:** Retargeted patches instead of implementing parameter injection (user correction).
**Root cause:** Focused on mechanical changes without reading plan context.
**Prevention:** Read plan context carefully - "enabling steps 1.3-1.5 to eliminate monkeypatching" reveals true goal.
**Recommendation:** ADD_TO_DOC

### 5. Plan Mode for Pre-Planned Tasks

**What happened:** Created plan file for `/erk:fix-conflicts` which already provides explicit instructions.
**Root cause:** Defaults to planning even when instructions exist.
**Prevention:** Check if command provides step-by-step instructions before entering plan mode.
**Recommendation:** TRIPWIRE (score 5)

### 6. Automated Bot False Positives

**What happened:** Bot flagged code that was either already fixed or intentionally designed that way.
**Root cause:** Bots apply production rules to test helpers without context.
**Prevention:** Always read flagged code and check if pattern exists elsewhere in function.
**Recommendation:** TRIPWIRE (score 6)

### 7. Test Helper Default Causes Matches

**What happened:** Default "test-user" matched query "user" in filter test.
**Root cause:** Default value overlapped with test data patterns.
**Prevention:** Verify defaults don't overlap with existing test data patterns.
**Recommendation:** TRIPWIRE (score 4)

### 8. Empty gh pr diff Output

**What happened:** `gh pr diff -- <path>` returned empty output.
**Root cause:** Invalid command syntax with path filter.
**Prevention:** Use `gh pr diff` without file path arguments, filter with grep if needed.
**Recommendation:** CONTEXT_ONLY

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Parameter Injection Test Updates

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1)
**Trigger:** Before adding required parameters to functions called by tests
**Warning:** "Grep ALL call sites in src/ and tests/ before implementation. Convert direct callers to parameter injection, retarget CLI test patches to import location."
**Target doc:** `docs/learned/testing/parameter-injection-pattern.md`

This tripwire prevents the HIGH-severity pattern of incomplete scope discovery that caused multiple rounds of test fixes in session c0f0f858.

### 2. False Positive Detection in Automated Reviews

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before making code changes based on automated review bot comments
**Warning:** "Read full function context to verify it's not a false positive. Check if fix is already in PR or if pattern is intentional (test factories)."
**Target doc:** `docs/learned/pr-operations/false-positive-detection.md`

This tripwire prevents unnecessary code changes and cluttered PR history from blindly following automated feedback.

### 3. Plan Mode When Explicit Instructions Exist

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before entering plan mode or using ExitPlanMode tool
**Warning:** "Check if current task has explicit step-by-step instructions. If yes, skip planning and proceed directly to execution."
**Target doc:** `docs/learned/planning/when-to-skip-planning.md`

This tripwire prevents redundant planning overhead when commands already provide decomposed steps.

### 4. Test Helper Defaults Overlapping with Queries

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, Silent failure +1)
**Trigger:** When adding defaults to test helper functions
**Warning:** "Verify default doesn't overlap with common test data patterns. Use distinct values like 'helper-default-author' not 'test-user'."
**Target doc:** `docs/learned/testing/test-helper-defaults.md`

### 5. Auto-Generated File Editing

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before editing files with `<!-- AUTO-GENERATED FILE -->` comment
**Warning:** "Apply STAMP ONLY approach - content edits will be overwritten by `erk docs sync`. Focus verification on source docs."
**Target doc:** `docs/learned/documentation/audit-auto-generated-files.md`

### 6. Import Removal Without Test Patch Updates

**Score:** 4/10 (Non-obvious +2, Destructive potential +2)
**Trigger:** Before removing imports from a module
**Warning:** "Grep test files for monkeypatch statements targeting this module. All patches must be converted to parameter injection or retargeted."
**Target doc:** `docs/learned/testing/import-location-patching.md`

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Filter Logic Without Test Update

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Adding filterable field broke test that now matched multiple fields. Could become tripwire if pattern repeats in future filter extensions.

### 2. Batch Resolution with Zero Code Changes

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Valid /erk:pr-address flow where all threads resolve without commits. Edge case but not dangerous.

### 3. Merged PR Precedence in Rebases

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Use `git checkout --ours` when base contains merged code. Good heuristic but low destructive potential.

### 4. Batch Editing Threshold (>30 files)

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Use sed instead of Edit tool. Performance optimization, not a safety issue.

### 5. Validation at Data Layer

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Architectural pattern, not a tripwire. Belongs in architecture docs.

### 6. Sentinel Values in Migrations

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Pattern for distinguishing migrated data. Useful convention, not dangerous if missed.

### 7. Illustrative Paths in Templates

**Score:** 2/10 (Non-obvious +2)
**Notes:** False positive avoidance during audits. Low impact if missed.

### 8. Test Factory Exemption from "No Defaults"

**Score:** 2/10 (Non-obvious +2)
**Notes:** Clarification needed for automated bots. Convention, not tripwire.