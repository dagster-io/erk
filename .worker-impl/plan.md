# Documentation Plan: [erk-plan] Address PR #7095 Review Comments (Batch 2)

## Context

This plan documents the learnings from PR #7113, which addressed two architectural issues raised in PR #7095: eliminating a circular dependency between `erk` and `erk_shared` packages, and adding HTML comment markers for reliable roadmap table detection. The implementation consolidated three scattered modules into a single comprehensive `roadmap.py` module in `erk_shared`, established a marker-based table detection system, and updated all consumers to use new import paths.

The documentation is valuable because it captures a mature refactoring pattern that future agents will encounter when working with the erk codebase. The circular dependency resolution demonstrates the correct approach for moving shared utilities between packages. The marker-based detection system establishes a pattern that could be applied to other content boundaries in GitHub metadata blocks.

Key non-obvious learnings include: the inline import pattern for breaking circular dependencies within the same package (which PR review bots may incorrectly flag), the three-tuple structure of `FakeGitHubIssues.added_comments` that agents frequently guess wrong, and the heredoc pattern for piping JSON to `erk exec` commands to avoid backslash escaping issues.

## Raw Materials

https://gist.github.com/schrockn/faed2d9bb5ec1a79c798b9f3354004dd

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 17    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These must be updated BEFORE creating new documentation to avoid confusing readers.

### 1. roadmap-parser-api.md Reference Updates

**Location:** `docs/learned/objectives/roadmap-parser-api.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` (MOVED)
**Cleanup Instructions:** Update all file path references to point to `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`. Affected sections include Lines 24, 49 (Module Location Anomaly), and all function source pointers.

### 2. roadmap-mutation-patterns.md Import Examples

**Location:** `docs/learned/objectives/roadmap-mutation-patterns.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** Import path changed for `_replace_step_refs_in_body()`
**Cleanup Instructions:** Update import examples to reflect new module path. The file still exists at `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` but imports now come from `erk_shared.gateway.github.metadata.roadmap`.

### 3. roadmap-parser.md Module Location

**Location:** `docs/learned/objectives/roadmap-parser.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** References to `objective_roadmap_shared.py` module
**Cleanup Instructions:** Update Line 28 reference to reflect that the module has moved to `erk_shared.gateway.github.metadata.roadmap`.

### 4. erk-shared-package.md Missing Modules

**Location:** `docs/learned/architecture/erk-shared-package.md`
**Action:** UPDATE_EXISTING
**Missing Content:** Package structure listing does not include roadmap utilities
**Cleanup Instructions:** Add roadmap utilities to the erk_shared package structure documentation. Include new submodule `erk_shared.gateway.github.metadata.roadmap` and `erk_shared.core.frontmatter`.

## Documentation Items

### HIGH Priority

#### 1. Circular Dependency Resolution Pattern

**Location:** `docs/learned/architecture/circular-dependency-resolution.md`
**Action:** CREATE
**Source:** [Impl], [PR #7113]

**Draft Content:**

```markdown
---
description: How to resolve circular dependencies between erk and erk_shared packages
globs: ["packages/erk-shared/**/*.py", "src/erk/**/*.py"]
category: architecture
last_audited: YYYY-MM-DD HH:MM PT
---

# Circular Dependency Resolution

## Problem

When `erk_shared` needs to import from `erk`, a circular dependency forms. This manifests as lazy imports (imports inside functions) to avoid ImportError at module load time.

## Solution

Move shared utilities to `erk_shared` so they are available to both packages. The package boundary rule is:

- `erk_shared` NEVER imports from `erk`
- `erk` CAN import from `erk_shared`

## Decision Framework

Utilities belong in `erk_shared` when:
1. Used by both `erk` and `erk_shared` packages
2. Have no `erk`-specific dependencies (CLI commands, TUI, etc.)
3. Operate on domain objects that `erk_shared` already defines

## Example

The roadmap utilities moved from `erk.cli.commands.exec.scripts` to `erk_shared.gateway.github.metadata.roadmap`. See `plan_issues.py` for the removed lazy imports pattern.

## Verification

Check for violations with: `grep -r 'from erk\.' packages/erk-shared/src/`

## Related

- `erk-shared-package.md` - Package structure overview
- `roadmap-utilities.md` - Specific example of this pattern
```

#### 2. HTML Comment Marker System

**Location:** `docs/learned/architecture/roadmap-table-markers.md`
**Action:** CREATE
**Source:** [Impl], [PR #7113]

**Draft Content:**

```markdown
---
description: HTML comment markers for 100% reliable roadmap table detection
globs: ["**/roadmap*.py", "**/update_roadmap_step.py"]
category: architecture
last_audited: YYYY-MM-DD HH:MM PT
---

# Roadmap Table Markers

## Problem

Regex-based table detection was fragile. Any 5-column markdown table matching the pattern would be modified, potentially corrupting unrelated content.

## Solution

HTML comment markers bound the roadmap section:
- Start: `<!-- erk:roadmap-table -->`
- End: `<!-- /erk:roadmap-table -->`

## Where Markers Are Added

`format_objective_content_comment()` in `core.py` wraps content with markers before rendering. See the inline import of `wrap_roadmap_tables_with_markers`.

## Where Markers Are Consumed

`_replace_table_in_text()` in `update_roadmap_step.py` uses `extract_roadmap_table_section()` to search only within markers when present.

## Backward Compatibility

When markers are absent (v1 objectives), falls back to full-text regex search. This maintains compatibility with objectives created before markers existed.

## Idempotency

`wrap_roadmap_tables_with_markers()` removes existing markers before adding new ones, preventing marker duplication.

## Public API

Constants `ROADMAP_TABLE_MARKER_START` and `ROADMAP_TABLE_MARKER_END` are public API in `roadmap.py`.

## Related

- `circular-dependency-resolution.md` - Why this uses inline import
- `exec-script-patterns.md` - Marker-bounded search pattern
```

#### 3. Inline Import Exception Pattern

**Location:** `docs/learned/architecture/dignified-python-core.md`
**Action:** UPDATE
**Source:** [PR #7113 comments]

**Draft Content:**

```markdown
## When Inline Imports ARE Acceptable

### Circular Dependency Within Same Package

When Module A imports from Module B at module level, and Module B needs to call a function in Module A, Module B must use an inline import to break the cycle.

**Example:** In `erk_shared.gateway.github.metadata`:
- `roadmap.py` imports `extract_raw_metadata_blocks` from `core.py` at module level (line 22)
- `core.py` needs `wrap_roadmap_tables_with_markers` from `roadmap.py`
- `core.py` uses inline import at line 737 to break the cycle

This is justified because both modules are in the same package and the circular dependency is inherent to their coupled functionality.

**PR Review Note:** Automated bots may flag this as a violation. Document the reasoning in a PR comment prefixed with "False positive: ..." so reviewers understand the justification.
```

### MEDIUM Priority

#### 4. Consolidated Roadmap Module Architecture

**Location:** `docs/learned/architecture/roadmap-utilities.md`
**Action:** CREATE
**Source:** [Impl], [Diff]

**Draft Content:**

```markdown
---
description: Architecture of the consolidated roadmap parsing and serialization module
globs: ["**/roadmap.py"]
category: architecture
last_audited: YYYY-MM-DD HH:MM PT
---

# Roadmap Utilities Module

## Location

`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`

## Why Consolidated

Three separate modules (`objective_roadmap_shared.py`, `objective_roadmap_frontmatter.py`, and parsing utilities) were consolidated into one because they:
1. Defined the same types (`RoadmapStep`, `RoadmapPhase`)
2. Operated on the same domain (objective roadmaps)
3. Required mutual imports within the same package

## Module Organization

1. **Data Types** - `RoadmapStepStatus`, `RoadmapStep`, `RoadmapPhase`
2. **Validation** - `validate_roadmap_frontmatter()`
3. **Parsing** - `parse_roadmap_frontmatter()`, `parse_roadmap()`
4. **Serialization** - `serialize_steps_to_frontmatter()`, `serialize_phases()`
5. **Utilities** - `group_steps_by_phase()`, `find_next_step()`, `compute_summary()`
6. **Markers** - `wrap_roadmap_tables_with_markers()`, `extract_roadmap_table_section()`

## Parsing Strategy

Frontmatter-first: tries YAML within objective-roadmap block, falls back to table parsing for v1 compatibility.

## Phase Grouping

Derives phases from step ID prefixes (e.g., "1.1" -> phase 1, "2A.1" -> phase 2A).

## Related

- `roadmap-table-markers.md` - Marker system details
- `circular-dependency-resolution.md` - Why module lives in erk_shared
```

#### 5. Phase Name Enrichment Pattern

**Location:** `docs/learned/architecture/phase-name-enrichment.md`
**Action:** CREATE
**Source:** [Diff]

**Draft Content:**

```markdown
---
description: Extracting phase names from markdown headers for roadmap display
globs: ["**/roadmap.py"]
category: architecture
last_audited: YYYY-MM-DD HH:MM PT
---

# Phase Name Enrichment

## Problem

Frontmatter stores steps with IDs like "1.1", "2A.3" but not phase names. Phase names exist only in markdown headers.

## Solution

`_enrich_phase_names()` extracts names from headers like "### Phase 1: Planning" and enriches phase objects.

## Algorithm

1. Regex matches phase headers in markdown body
2. Builds map of `(phase_number, suffix)` -> `name`
3. Iterates through phases, using `dataclasses.replace()` to set name field

## Usage

Called after `group_steps_by_phase()` to complete the phase data.

## Regex Pattern

See `_enrich_phase_names()` in `roadmap.py` for the header matching pattern.
```

#### 6. Marker-Bounded Search Pattern

**Location:** `docs/learned/cli/exec-script-patterns.md`
**Action:** UPDATE
**Source:** [Diff]

**Draft Content:**

```markdown
## Marker-Bounded Search Pattern

When searching for content that may appear multiple times (like markdown tables), use markers to bound the search region.

### Pattern

1. Check for markers: `section = extract_roadmap_table_section(text)`
2. If markers found: search only within `section`
3. If markers absent: fall back to full-text search (backward compatibility)

### Benefits

- Avoids false positives (matching wrong table)
- 100% reliable detection when markers present
- Maintains v1 compatibility when markers absent

### Example

See `_replace_table_in_text()` in `update_roadmap_step.py` for implementation.
```

#### 7. False Positive Resolution Workflow

**Location:** `docs/learned/reviews/false-positive-resolution-workflow.md`
**Action:** CREATE
**Source:** [PR #7113 comments]

**Draft Content:**

```markdown
---
description: PR review workflow for handling justified exceptions to coding standards
globs: ["**/*.py"]
category: reviews
last_audited: YYYY-MM-DD HH:MM PT
---

# False Positive Resolution Workflow

## When Automated Reviewers Flag Justified Code

1. **Identify the false positive** - Understand why the code is correct despite the flag
2. **Document in PR comment** - Reply with "False positive: ..." prefix explaining the justification
3. **Request re-review** - Summary review should include "False Positive Resolution" section
4. **Resolve thread** - Mark thread resolved after explanation accepted

## Example

PR #7113 core.py:737 inline import was flagged by dignified-python bot. Response documented circular dependency justification. Thread resolved with explanation.

## Why This Matters

Future reviewers (human or AI) can see the reasoning inline rather than re-investigating.
```

#### 8. Test Coverage Review Standards

**Location:** `docs/learned/testing/test-coverage-review-standards.md`
**Action:** CREATE
**Source:** [PR #7113 comments]

**Draft Content:**

```markdown
---
description: Standards for evaluating test coverage beyond "test file exists"
globs: ["tests/**/*.py"]
category: testing
last_audited: YYYY-MM-DD HH:MM PT
---

# Test Coverage Review Standards

## Beyond "Test File Exists"

Test coverage review should evaluate:

1. **Edge case coverage** - Missing phases, duplicate markers, malformed input
2. **Quantitative metrics** - Lines of test code relative to implementation
3. **Explicit enumeration** - List test scenarios in review comments

## Example

PR #7113 marker tests: 1,300+ test lines for 742-line module. Review explicitly enumerated scenarios:
- Wrapping: adds markers, handles no phases, replaces existing, wraps single/multiple
- Extraction: returns section, returns None without markers, handles incomplete

## What to Look For

- Are error paths tested?
- Are boundary conditions covered?
- Is the test data realistic?
```

#### 9. Roadmap Marker Testing Patterns

**Location:** `docs/learned/testing/roadmap-marker-testing.md`
**Action:** CREATE
**Source:** [Diff]

**Draft Content:**

```markdown
---
description: Testing patterns for HTML comment marker wrapping and extraction
globs: ["**/test_roadmap_markers.py"]
category: testing
last_audited: YYYY-MM-DD HH:MM PT
---

# Roadmap Marker Testing

## Test Coverage Categories

### Marker Wrapping (`wrap_roadmap_tables_with_markers`)
- Adds markers around phase sections
- Handles content with no phases (no-op)
- Replaces existing markers (idempotency)
- Wraps single phase correctly
- Wraps multiple phases correctly

### Marker Extraction (`extract_roadmap_table_section`)
- Returns section content between markers
- Returns None when markers absent
- Handles incomplete markers (only start, only end)
- Returns correct offsets for replacement

## Test Data Patterns

Use inline markdown strings with phase headers and tables. Keep test data self-contained in each test function.

## Assertion Patterns

- Check marker presence in output
- Verify section content matches expected
- Validate start/end offsets enable correct replacement
```

#### 10. FakeGitHubIssues Tuple Structures

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

```markdown
## FakeGitHubIssues Data Structures

When writing tests that verify issue/comment creation, verify tuple structures by reading the fake source. Do not assume.

### Tuple Formats

| Property | Structure | Fields |
|----------|-----------|--------|
| `created_issues` | 3-tuple | `(title, body, labels)` |
| `added_comments` | 3-tuple | `(issue_number, body, comment_id)` |
| `updated_bodies` | 2-tuple | `(issue_number, body)` |

### Why This Matters

Agents frequently guess the `added_comments` structure as 2-tuple `(issue_number, body)`, causing `ValueError: too many values to unpack`. Always read `FakeGitHubIssues` source.
```

#### 11. Test Migration Pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Diff]

**Draft Content:**

```markdown
## Test Migration: erk to erk_shared

When code moves from `erk` to `erk_shared`, tests follow.

### Directory Mapping

| erk Location | erk_shared Location |
|--------------|---------------------|
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_*.py` | `packages/erk-shared/tests/unit/github/metadata/test_roadmap*.py` |
| `tests/unit/core/test_frontmatter.py` | `packages/erk-shared/tests/unit/core/test_frontmatter.py` |

### Migration Checklist

1. Move test file to corresponding erk_shared location
2. Update imports from `erk.` to `erk_shared.`
3. Update any file path references in test data
4. Verify tests pass in new location
```

#### 12. Parallel Exploration Strategy

**Location:** `docs/learned/planning/planning.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

```markdown
## Parallel Exploration for Multi-Issue PRs

When addressing multiple independent review comments, launch parallel Explore agents rather than investigating sequentially.

### Pattern

1. Identify independent issues (no shared context required)
2. Launch parallel Explore agents for each issue
3. Read key files after exploration to validate findings
4. Consolidate findings before writing plan

### Example

PR #7095 Batch 2: circular dependency and table parsing investigated in parallel, then findings consolidated into single plan.

### Benefits

- Faster context gathering
- Avoids sequential bottleneck
- Each agent specializes in one issue
```

### LOW Priority

#### 13. Update roadmap-format-versioning.md

**Location:** `docs/learned/objectives/roadmap-format-versioning.md`
**Action:** UPDATE
**Source:** [Diff]

**Draft Content:**

```markdown
## v1 to v2 Migration

### PR Column Migration

v1 format stored plan reference in PR column: "plan #NNN"
v2 format has dedicated `plan` field in frontmatter

Migration logic in `validate_roadmap_frontmatter()` detects "plan #NNN" pattern and extracts to `plan` field.
```

#### 14. Graphite Workflow

**Location:** `docs/learned/erk/git-workflow.md`
**Action:** UPDATE (or CREATE if missing)
**Source:** [Impl]

**Draft Content:**

```markdown
## Graphite-Managed Branches

For branches managed by Graphite, use `gt submit` instead of `git push`.

### Why

- Graphite tracks branch relationships for stacking
- Direct push bypasses Graphite's metadata updates
- `gt submit --no-interactive` ensures CI-safe execution

### After Rebase

If local history diverges from remote after rebase:
1. Use `/erk:sync-divergence` skill
2. Or manually: `gt track` -> `gt restack` -> `gt submit`
```

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Pre-Existing Test Failures When Changing Formats

**What happened:** Tests were written for v1 format (content in body) but implementation changed to v2 (metadata in body, content in comment). Three tests failed unexpectedly.
**Root cause:** Format change was made without updating all tests in the same commit.
**Prevention:** When changing data format (v1->v2), update ALL tests in the same commit. Run full test suite before marking PR ready.
**Recommendation:** TRIPWIRE

### 2. JSON Escaping in Bash Echo

**What happened:** Piping JSON via `echo '[...]' | erk exec ...` caused JSON parsing error due to backslash interpretation.
**Root cause:** Bash interprets backslashes in double-quoted strings, corrupting JSON escape sequences.
**Prevention:** Use heredoc syntax: `cat <<'JSONEOF' | erk exec ...` with unescaped JSON.
**Recommendation:** TRIPWIRE

### 3. Incorrect Fake Tuple Unpacking

**What happened:** Agent assumed `fake_gh.added_comments[0]` returned 2-tuple but it returns 3-tuple `(issue_number, body, comment_id)`.
**Root cause:** Guessed tuple structure without reading fake source.
**Prevention:** Always read fake gateway source when writing tests. Don't assume tuple structures.
**Recommendation:** ADD_TO_DOC (testing.md)

### 4. Git Push Rejected After Rebase

**What happened:** Direct `git push` failed with non-fast-forward error after rebasing.
**Root cause:** Local history rewritten (WIP commit removed), remote still had old history.
**Prevention:** Use `gt submit` for Graphite repos instead of `git push`. For rebase conflicts, use `/erk:sync-divergence`.
**Recommendation:** ADD_TO_DOC (git-workflow.md)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Circular Dependency erk_shared -> erk

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before importing from `erk` package in `erk_shared` code
**Warning:** STOP. erk_shared NEVER imports from erk. Move shared utilities to erk_shared. Verify with `grep -r 'from erk\.' packages/erk-shared/src/`
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the violation creates subtle circular dependencies that manifest as lazy imports or runtime errors. The damage is structural and affects multiple files.

### 2. Pre-Existing Test Failures When Changing Data Format

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When changing data format between versions (v1->v2)
**Warning:** Update ALL tests in same commit. Run full test suite before marking PR ready. Format changes affect multiple test files.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because format changes silently break tests that were written for the old format. The agent may not realize tests exist elsewhere in the codebase.

### 3. JSON Escaping in Bash Heredoc Pattern

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When piping JSON to `erk exec` commands via `echo`
**Warning:** Use heredoc syntax `cat <<'JSONEOF' | erk exec ...` instead of `echo '[...]' | erk exec ...` to avoid backslash escaping issues.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the escaping error is subtle and the error message ("JSON parsing error") doesn't indicate the root cause.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Import Sorting After Refactoring

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** Caught by CI but slows iteration. Consider adding to pre-commit hook auto-fix list. Low severity because CI catches it before merge.

### 2. Format Check After Write Operations

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** Similar to import sorting - CI catches but slows flow. Could add `make format` reminder after Write tool usage.

### 3. Fake Tuple Structure Verification

**Score:** 3/10 (criteria: Non-obvious +2, Silent failure +1)
**Notes:** Agent guessed wrong tuple structure. Should read fake source. Low severity because tests fail fast with clear error message.

### 4. Parallel Exploration for Multi-Issue PRs

**Score:** 2/10 (criteria: Cross-cutting +2)
**Notes:** More of a best practice than a tripwire. Document in planning.md instead of creating a tripwire.