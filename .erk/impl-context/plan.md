# Document flat format elimination and metadata block adoption

## Context

PR #8165 eliminated the "flat format" separator-based metadata extraction system and replaced it with the general metadata block system. The core change was removing the `extract_plan_header_block` function and replacing all callers with `find_metadata_block()` + `render_metadata_block()` from the general metadata system. The `PLAN_CONTENT_SEPARATOR` constant is retained only for backward compatibility in `extract_plan_content` for old PRs.

This documentation work is critical because the existing documentation contains phantom references to functions that never existed (`extract_metadata_prefix()`) and describes patterns that have now been eliminated. The tripwires bot caught documentation drift during PR review, validating the "documentation is code" philosophy. Without these updates, agents will attempt to use deprecated functions and patterns, causing confusion and wasted time.

The implementation sessions revealed several valuable patterns: the multi-agent discovery workflow (parallel Explore agents followed by a Plan agent), the plan-mode follow-up workflow for iterative development, and critical lessons about test helper updates when refactoring formats. These patterns deserve documentation for future agents.

## Raw Materials

PR #8165

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 18    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. Fix function name phantom references

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`, `docs/learned/planning/tripwires.md`
**Action:** UPDATE_REFERENCES
**Source:** [PR #8165]

**Draft Content:**

```markdown
<!-- NOTE: This doc previously referenced `extract_metadata_prefix()` which never existed.
     The actual function was `extract_plan_header_block()`, which was deleted in PR #8165.

     CURRENT APPROACH: Use metadata block system from `erk_shared.gateway.github.metadata.core`:
     - `find_metadata_block(text, "plan-header")` to locate plan-header metadata
     - `render_metadata_block(block)` to convert back to text if needed

     See packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py for implementation.
-->
```

---

#### 2. Document metadata block system adoption for planned PRs

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
## Metadata Extraction (Updated in PR #8165)

### Historical Context

Prior to PR #8165, planned PR bodies used a separator-based extraction system with `PLAN_CONTENT_SEPARATOR` (`\n\n---\n\n`). The function `extract_plan_header_block()` extracted everything up to and including this separator.

### Current Approach

All metadata extraction now uses the general metadata block system from `erk_shared.gateway.github.metadata.core`:

- **Detection:** Metadata blocks are wrapped in self-delimiting HTML comment markers (`<!-- erk:metadata-block:plan-header -->`)
- **Extraction:** Use `find_metadata_block(pr_body, "plan-header")` to locate the block
- **Rendering:** Use `render_metadata_block(block)` to convert a parsed block back to text

### Backward Compatibility

`PLAN_CONTENT_SEPARATOR` is retained ONLY for backward compatibility in `extract_plan_content()` for old PRs that predate the metadata block system. New code should never use this constant for format detection or construction.

See `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py` for the authoritative implementation.
```

---

#### 3. Update "Three Eras" to "Four Eras"

**Location:** `docs/learned/planning/metadata-block-fallback.md`
**Action:** UPDATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
## Format Evolution

| Era | Format | Detection | Status |
|-----|--------|-----------|--------|
| v0  | Raw markdown | None | Legacy |
| v1  | Details tags with flat content | `<details><summary>` without metadata markers | Legacy |
| v2  | Metadata blocks with separators | `<!-- erk:metadata-block:*` + `PLAN_CONTENT_SEPARATOR` | Deprecated |
| v3  | Pure metadata blocks | `<!-- erk:metadata-block:*` self-delimiting (no separator) | Current |

**v3 (PR #8165):** Eliminated separator-based extraction entirely. Metadata blocks are now self-delimiting via HTML comment markers, making the `PLAN_CONTENT_SEPARATOR` unnecessary for format boundaries. The constant is retained only for backward-compatible reading of old PRs.
```

---

#### 4. Document extraction pattern migration

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
## Extraction Pattern Migration

### Old Pattern (Removed in PR #8165)

The old pattern used separator-based extraction that coupled format detection with content extraction:

```python
plan_header_block = extract_plan_header_block(pr_body)
metadata = plan_header_block.removesuffix(PLAN_CONTENT_SEPARATOR)
```

### New Pattern (Current)

The new pattern uses the general metadata block system, which is position-agnostic and self-delimiting:

```python
plan_header = find_metadata_block(pr_body, "plan-header")
metadata_text = render_metadata_block(plan_header) if plan_header is not None else ""
```

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` for `find_metadata_block` and `render_metadata_block` implementations.

### Key Differences

1. **Position-agnostic:** `find_metadata_block()` works regardless of where the metadata appears in the PR body
2. **Self-delimiting:** HTML comment markers define boundaries, no separator needed
3. **Unified system:** Same extraction pattern works for all metadata block types, not just plan-header
```

---

#### 5. Automated review bot documentation

**Location:** `docs/learned/ci/automated-reviews.md`
**Action:** CREATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
---
title: Automated Review Bot System
read-when: working with CI reviews, understanding automated feedback, debugging review bot comments
category: ci
---

# Automated Review Bot System

## Overview

Erk uses a three-tier automated review system that catches different categories of issues:

## Tier 1: Style (Dignified Code Simplifier)

- **Focus:** Formatting, code structure, consistency
- **Catches:** Indentation, line length, import ordering
- **Example bot:** Dignified Code Simplifier

## Tier 2: Standards (Dignified Python)

- **Focus:** Python conventions, typing, patterns
- **Catches:** LBYL violations, mutable defaults, relative imports
- **Example bot:** Dignified Python Review

## Tier 3: Semantics (Tripwires)

- **Focus:** Documentation drift, architectural violations, cross-cutting concerns
- **Catches:** Phantom references in docs, deprecated pattern usage
- **Example bot:** Tripwires Bot

## Key Insight from PR #8165

Only the semantic review tier (Tripwires) caught documentation drift that would have caused agent confusion. Style and standards bots reported no violations, demonstrating that:

- Semantic review is more valuable than style review for catching meaningful issues
- Documentation updates should be part of the PR, not follow-up work
- Stale docs are a genuine failure mode in refactoring projects

## When Automated Review is Sufficient

PR #8165 had zero human review comments, only automated feedback. This is acceptable when:
- Changes are well-tested (5734 tests passing)
- Semantic review catches meaningful issues
- Implementation follows established patterns
```

---

#### 6. Update planning tripwires

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
<!-- REMOVED: The following tripwires referenced functionality deleted in PR #8165 -->
<!-- - Separator validation: No longer needed, metadata blocks are self-delimiting -->
<!-- - extract_metadata_prefix() usage: Function never existed (was always extract_plan_header_block) -->
<!-- - extract_plan_header_block() usage: Function deleted, use find_metadata_block() instead -->
<!-- - Flat format handling: Format eliminated, only metadata block system remains -->

## Current Tripwires

### Before calling gt submit
Always capture existing PR body first using `capture_existing_pr_body()` to prevent metadata loss when gt overwrites the body.

### When modifying PR body assembly
Always use `find_metadata_block()` from `erk_shared.gateway.github.metadata.core` instead of custom extraction. This prevents regression to deprecated patterns.

### When working with plan-header metadata
Use `metadata/core.py` functions (`find_metadata_block`, `replace_metadata_block_in_body`) not custom extraction. Ensures consistency across all metadata operations.
```

---

### MEDIUM Priority

#### 7. PR body construction pattern consolidation

**Location:** `docs/learned/planning/pr-body-construction.md`
**Action:** CREATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
---
title: PR Body Construction Patterns
read-when: constructing planned PR bodies, understanding stage transitions, modifying PR body assembly
category: planning
---

# PR Body Construction Patterns

## Overview

Planned PR bodies are constructed through several stages. After PR #8165, all stages use the metadata block system.

## Stage 1: Plan Creation

Use `build_plan_stage_body(metadata_body, content)` from `planned_pr_lifecycle.py`:

- Metadata rendered via `render_metadata_block()`
- Content wrapped in `<details>` tags
- Joined with `\n\n` (no separator constant)

## Stage 2: Implementation

Use `assemble_pr_body()` from `src/erk/cli/commands/pr/shared.py`:

- Extracts metadata via `find_metadata_block(pr_body, "plan-header")`
- Rebuilds body with implementation details

## CI Updates

Use `_update_pr_body_impl()` from `ci_update_pr_body.py`:

- Same extraction pattern as Stage 2
- Preserves metadata while updating content sections

## Source Files

See the implementations in:
- `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py`
- `src/erk/cli/commands/pr/shared.py`
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
```

---

#### 8. Test helper update pattern

**Location:** `docs/learned/testing/format-refactoring-tests.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Test Helper Update Pattern for Format Refactoring
read-when: refactoring data formats, updating test fixtures, changing body construction functions
category: testing
---

# Test Helper Update Pattern

## Problem

When refactoring production code that changes data formats (e.g., PR body structure, metadata format), tests can fail subtly because:
1. Test helpers construct data in the old format
2. Test assertions verify the old format structure
3. Multiple test files depend on shared helpers

## Discovery

This pattern was identified during PR #8165 implementation when tests expected `"\n\n---\n\n"` separator in results but the new implementation no longer included it.

## Checklist

When refactoring format functions:

1. **Grep for all test helpers** that construct test data:
   - `tests/test_utils/` directory
   - `format_*_for_test` functions
   - `build_*` helper functions

2. **Update fixture construction** to match new format:
   - Change separators/delimiters as needed
   - Update any format-specific construction logic

3. **Update test assertions** to verify new format:
   - Change `assert x in result` to `assert x not in result` if element removed
   - Add assertions for new format elements

4. **Run targeted tests first** before full CI to catch format mismatches early

## Example from PR #8165

- Updated `tests/test_utils/plan_helpers.py` to use `\n\n` instead of `PLAN_CONTENT_SEPARATOR`
- Changed assertion from `assert "\n\n---\n\n" in result` to `assert "\n\n---\n\n" not in result`
- Affected 5 test files across the codebase

## Files to Check

See `tests/test_utils/` for common test helpers, especially:
- `plan_helpers.py` for planned PR format helpers
- Any `*_for_test` functions that construct structured data
```

---

#### 9. Multi-agent discovery pattern

**Location:** `docs/learned/planning/agent-orchestration.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Multi-Agent Discovery Pattern
read-when: planning complex features, orchestrating multiple agents, gathering information before planning
category: planning
---

# Multi-Agent Discovery Pattern

## Overview

For complex planning tasks, use parallel Explore agents to gather facts before launching a Plan agent. This pattern was demonstrated in the PR #8165 implementation session.

## Workflow

1. **Launch parallel Explore agents** to gather facts about different aspects:
   - Agent 1: Analyze current implementation state
   - Agent 2: Find existing patterns and references

2. **Wait for completion** of all Explore agents

3. **Verify key details** by reading critical files directly (don't trust agent summaries alone)

4. **Launch Plan agent** with complete context from Explore results

5. **Write plan to file** for persistence

6. **Present options to user** via AskUserQuestion

## Example from PR #8165

Two parallel Explore agents were launched:
- Agent 1: Analyzed metadata block positioning across all PR body construction paths
- Agent 2: Explored backfill patterns and how to list/update open planned PRs

Both agents were instructed to "FIRST check docs/learned/index.md for existing documentation" before exploring code.

## Benefits

- **Parallel execution** speeds up information gathering
- **Separation of concerns** keeps each agent focused
- **Verification step** catches agent hallucinations
- **Complete context** enables better planning
```

---

#### 10. Plan-mode follow-up workflow

**Location:** `docs/learned/planning/iterative-planning.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Plan-Mode Follow-Up Workflow
read-when: creating follow-up plans, iterating on implementations, building on previous PRs
category: planning
---

# Plan-Mode Follow-Up Workflow

## Overview

After completing an implementation, you may want to create a follow-up plan that builds on the work. This workflow demonstrates the complete plan-first loop for iterative development.

## Complete Workflow

1. **Implement plan A** in a worktree slot
2. **Submit PR for plan A** via `gt submit` or `erk pr submit`
3. **Enter plan mode** for follow-up work (user says "plan" or enters `/plan`)
4. **Use multi-agent discovery** to understand current state:
   - Launch parallel Explore agents
   - Gather information about what to build next
5. **Design plan B** via Plan agent with context from discovery
6. **Save plan B as draft PR** via `/erk:plan-save`
7. **Implement plan B later** in a fresh session with clean context

## Example from PR #8165

After implementing separator elimination:
1. User requested follow-up: "move metadata blocks to bottom + backfill open PRs"
2. Agent launched 2 Explore agents in parallel
3. Agent launched Plan agent with combined context
4. Plan saved as draft PR #8169
5. Implementation deferred to separate session

## Key Insight

This pattern enables iterative development where each PR builds on the previous one. The planning session stays lightweight (no implementation), preserving context for complex planning tasks.
```

---

#### 11. Conflict hotspots

**Location:** `docs/learned/ci/conflict-hotspots.md`
**Action:** CREATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
---
title: Conflict Hotspots
read-when: rebasing branches, resolving merge conflicts, understanding which files frequently conflict
category: ci
---

# Conflict Hotspots

## Overview

Certain files in the erk codebase frequently conflict during rebases due to high change velocity or structural dependencies.

## Known Hotspots

Files that frequently conflict (observed during PR #8165 with 7 conflicts in one rebase):

### `.claude/skills/` directory
- Skill definitions evolve rapidly
- Multiple PRs often modify the same skills
- **Mitigation:** Review skill changes carefully, consider splitting skill modifications into separate PRs

### `plan_store` modules
- Core planning functionality with many callers
- Format changes affect multiple files simultaneously
- **Mitigation:** Plan format changes carefully, update all callers in single PR

### CI scripts and tests
- CI configuration is a shared dependency
- Test utilities used across many test files
- **Mitigation:** Run `erk exec reconcile-with-remote` early and often

## Handling Conflicts

When conflicts occur in these files:
1. Use `/erk:fix-conflicts` for automated resolution
2. Verify format consistency after resolution
3. Re-run affected tests before pushing
```

---

#### 12. Test coverage bot expectations

**Location:** `docs/learned/testing/test-coverage-review.md`
**Action:** CREATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
---
title: Test Coverage Bot Expectations
read-when: responding to test coverage bot comments, understanding what the bot checks for
category: testing
---

# Test Coverage Bot Expectations

## Overview

The test coverage bot checks for *appropriate updates* to tests, not just coverage percentage. This is more sophisticated than simple coverage metrics.

## What the Bot Checks

### Positive Signals
- Removing tests for deleted functions (cleanup)
- Updating assertions for new behavior
- Adding tests for new functionality

### What It's NOT Checking
- Raw coverage percentage
- Line-by-line coverage metrics
- Test count thresholds

## Example from PR #8165

When `extract_plan_header_block()` was deleted:
- Bot verified corresponding tests were removed
- Bot verified new assertions matched new behavior (`assert separator not in result`)
- No coverage percentage complaints despite removing tests

## Implications

When making changes:
- Delete tests for removed functionality (don't leave dead tests)
- Update assertions to match new behavior
- The bot understands that fewer tests can be appropriate
```

---

### LOW Priority

#### 13. Branch slug generation rules

**Location:** `docs/learned/planning/branch-naming.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Branch Slug Generation Rules
read-when: generating branch names for plans, understanding slug conventions
category: planning
---

# Branch Slug Generation Rules

## Rules

When generating a branch slug from a plan title:

1. **Length:** 2-4 hyphenated lowercase words
2. **Maximum:** 30 characters total
3. **Drop filler words:** the, a, for, implementation, plan, system
4. **Prefer action verbs:** eliminate, move, add, fix, update

## Example

**Title:** "Move Metadata Blocks to Bottom of PR Body + Backfill Open Planned PRs"

**Slug generation process:**
1. Extract key words: move, metadata, bottom, backfill
2. Drop fillers: (none in this case)
3. Combine: `move-metadata-bottom-backfill`
4. Verify length: 27 chars (under 30)

**Result:** `move-metadata-bottom-backfill`

## Usage

The `/erk:plan-save` skill generates slugs automatically. For manual branch creation, follow these rules to maintain consistency.
```

---

#### 14. Inline Python for PR analysis

**Location:** `docs/learned/cli/pr-inspection-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: PR Inspection Patterns
read-when: inspecting PR content programmatically, analyzing PR body format, debugging PR issues
category: cli
---

# PR Inspection Patterns

## Inline Python for PR Analysis

When you need to inspect PR content programmatically, pipe `gh pr view` output to inline Python:

```bash
gh pr view 8146 --json body | python3 -c "
import json, sys
body = json.load(sys.stdin)['body']
# Analyze the body...
print(body[:500])
"
```

## Use Cases

1. **Format inspection:** Verify metadata block structure before migration
2. **Content extraction:** Pull specific sections from PR body
3. **Validation:** Check for expected patterns or missing content

## Best Practice

Before modifying PR format (e.g., backfill operations):
1. Inspect at least one real PR with live data
2. Create dry-run capability first
3. Test on single PR before batch operations

This pattern was used in PR #8165 planning to understand current metadata block positioning before proposing changes.
```

---

#### 15. Hook-driven workflow control

**Location:** `docs/learned/hooks/workflow-control.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Hook-Driven Workflow Control
read-when: understanding how hooks control agent behavior, implementing workflow gates
category: hooks
---

# Hook-Driven Workflow Control

## Overview

Hooks can intercept agent actions and redirect workflow at critical decision points. This is demonstrated by the `ExitPlanMode` hook.

## Example: ExitPlanMode Hook

When an agent attempts to exit plan mode, the `PreToolUse:ExitPlanMode` hook:

1. **Intercepts** the exit attempt
2. **Returns error** with instructions to use `AskUserQuestion`
3. **Redirects** agent to present three options:
   - Create a plan PR (Recommended)
   - Skip PR and implement now
   - View/Edit the plan
4. **Executes** user's choice

## Pattern

Hooks as workflow control:
- **Gate:** Prevent automatic progression
- **Redirect:** Point to correct workflow path
- **Preserve choice:** Let user decide at decision points

## Implementation Notes

The hook returns an error message containing the exact structure the agent should use for `AskUserQuestion`. This ensures consistent UX across all plan-mode exits.

See `.claude/hooks/` for hook implementations.
```

---

#### 16. Position-agnostic extraction note

**Location:** `docs/learned/architecture/metadata-blocks.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Position-Agnostic Extraction

Both `find_metadata_block()` and `extract_plan_content()` are position-agnostic. They can find and extract content regardless of where the metadata block appears in the PR body (top or bottom).

This design enables safe migration of metadata block positioning without breaking extraction logic. PR #8165 leveraged this to eliminate separator-based extraction, and the follow-up work (PR #8169) can safely move metadata to the bottom knowing extraction will still work.

See `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py` for implementation.
```

---

#### 17. Backend-agnostic planning notes

**Location:** `docs/learned/planning/` (multiple files)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Backend-Agnostic Planning

The planning system supports multiple backends for storing plans:

- **planned_pr:** Plans stored as draft PRs (current default)
- **issue:** Plans stored as GitHub issues

The `/erk:plan-save` output includes `"plan_backend": "planned_pr"` to indicate which backend was used. Skill instructions include conditional logic to display appropriate next steps based on the backend.

When writing documentation about planning, avoid assuming a specific backend unless the context clearly requires it.
```

---

#### 18. PR body format evolution reference

**Location:** `docs/learned/planning/pr-body-format-evolution.md`
**Action:** CREATE
**Source:** [PR #8165]

**Draft Content:**

```markdown
---
title: PR Body Format Evolution
read-when: understanding PR body format history, debugging format issues in old PRs
category: planning
---

# PR Body Format Evolution

## Current Format (Post-PR #8165)

```
<!-- erk:metadata-block:plan-header -->
<details>
<summary>plan-header</summary>

```yaml
title: Plan Title
status: draft
...
```

</details>
<!-- /erk:metadata-block:plan-header -->

<details>
<summary>original-plan</summary>

[plan content]

</details>
```

## Previous Format (Pre-PR #8165)

```
<!-- erk:metadata-block:plan-header -->
<details>
<summary>plan-header</summary>

```yaml
title: Plan Title
...
```

</details>
<!-- /erk:metadata-block:plan-header -->

---

<details>
<summary>original-plan</summary>

[plan content]

</details>
```

## Key Difference

The `\n\n---\n\n` separator between metadata and content was eliminated. Metadata blocks are now self-delimiting via HTML comment markers.

## Backward Compatibility

`extract_plan_content()` still handles old separator format for reading existing PRs. New PRs use the current format exclusively.
```

---

## Contradiction Resolutions

### 1. Function naming inconsistency: `extract_metadata_prefix()` vs `extract_plan_header_block()`

**Existing doc:** `docs/learned/planning/planned-pr-lifecycle.md`, `docs/learned/planning/tripwires.md`
**Conflict:** Documentation refers to a function called `extract_metadata_prefix()` but the actual codebase has always used `extract_plan_header_block()`. No function named `extract_metadata_prefix()` exists anywhere in the codebase.

**Resolution:** Update all documentation to:
1. Remove all references to `extract_metadata_prefix()` (it never existed)
2. Note that `extract_plan_header_block()` was deleted in PR #8165
3. Document the replacement pattern using `find_metadata_block()` + `render_metadata_block()`

This phantom reference likely occurred because documentation was written from memory rather than by reading the actual code. The tripwires bot should be updated to catch such phantom references.

---

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. planned-pr-lifecycle.md phantom references

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `extract_metadata_prefix()` (never existed), references to separator-based format now eliminated
**Cleanup Instructions:**
- Replace all `extract_metadata_prefix()` references with note about `find_metadata_block()`
- Update sections on separator semantics to indicate format was eliminated
- Update backward compatibility section to clarify `PLAN_CONTENT_SEPARATOR` scope

### 2. planning/tripwires.md phantom references

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Phantom References:** Separator validation tripwires, `extract_metadata_prefix()` usage warnings
**Cleanup Instructions:**
- Remove or update tripwires referencing separator validation
- Remove references to `extract_metadata_prefix()`
- Add new tripwires for metadata block system usage

### 3. metadata-block-fallback.md missing era

**Location:** `docs/learned/planning/metadata-block-fallback.md`
**Action:** UPDATE
**Phantom References:** "Three eras" table is now incomplete
**Cleanup Instructions:** Add fourth era for pure metadata blocks without separators (v3)

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Test assertions expecting old format

**What happened:** After changing production code to remove separator, tests still expected `"\n\n---\n\n"` in results
**Root cause:** Test assertions were written to verify old format structure
**Prevention:** After changing production code format, systematically search and update all test assertions that verify format structure
**Recommendation:** ADD_TO_DOC (covered in format-refactoring-tests.md)

### 2. Prettier on Python files

**What happened:** Agent ran `prettier --write` on a Python file, causing CI failure
**Root cause:** Prettier is designed for web languages and cannot infer a parser for `.py` files
**Prevention:** Always use `ruff format` for Python files, never `prettier`
**Recommendation:** TRIPWIRE

### 3. Test helpers using old format

**What happened:** Test helper functions in `plan_helpers.py` constructed data in old format
**Root cause:** When refactoring format functions, test helpers weren't updated
**Prevention:** When refactoring format functions, grep for all test helpers and update fixture construction
**Recommendation:** ADD_TO_DOC (covered in format-refactoring-tests.md)

### 4. Metadata loss on PR update (gt submit)

**What happened:** Historical issue where `gt submit` silently overwrites entire PR body
**Root cause:** gt submit doesn't preserve existing body content
**Prevention:** Always capture existing PR body first using `capture_existing_pr_body()`
**Recommendation:** TRIPWIRE (already in AGENTS.md but worth reinforcing)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Metadata loss on PR update (gt submit)

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before calling `gt submit`
**Warning:** "Always capture existing PR body first using `capture_existing_pr_body()` to prevent metadata loss when gt overwrites the body"
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because gt submit silently overwrites the entire PR body without warning. Metadata loss affects all planned PRs and is unrecoverable without manual reconstruction. The failure is completely silent - the PR updates successfully but loses all metadata blocks.

### 2. Missing --no-interactive on gt commands

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before calling any gt command
**Warning:** "Always pass `--no-interactive` flag. The `--interactive` flag is enabled by default and may prompt for input, hanging indefinitely"
**Target doc:** `docs/learned/erk/tripwires.md` or universal tripwires

This is already documented in AGENTS.md but agents still occasionally miss it. The failure mode (hanging indefinitely waiting for input) is particularly problematic for automated workflows.

### 3. Python formatter selection

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** Before running formatters on Python files
**Warning:** "Use `ruff format`, never `prettier`. Prettier cannot infer parser for .py files and will fail"
**Target doc:** `docs/learned/testing/tripwires.md`

This was discovered during PR #8165 implementation when the agent ran prettier on a Python file, causing CI failure. The error message ("could not infer parser") is not immediately obvious. This affects any Python formatting operation.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test helper update on format refactoring

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** High severity when it occurs but specific to format refactoring. Would become tripwire-worthy if this pattern recurs in multiple PRs. Currently documented as a checklist item in format-refactoring-tests.md.

### 2. Metadata block detection pattern

**Score:** 3/10 (Cross-cutting +2, External tool quirk +1)
**Notes:** Using `find_metadata_block(text, key)` instead of custom extraction is the correct pattern but missing it causes obvious errors (function not found), not silent failures. Not quite at tripwire level.

### 3. Function elimination grep discipline

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Always grep for all references when deleting functions. Good practice but failures are usually caught by tests or type checker, not silent.

### 4. PR format inspection before modification

**Score:** 3/10 (Non-obvious +2, Destructive potential +1)
**Notes:** Inspect real PRs before backfill operations. Important for preventing mass corruption but testing usually catches issues before production impact.
