# Documentation Plan: planned/ LLM-generated branch name slugs for meaningful naming

## Context

PR #7853 introduced LLM-powered branch name slug generation into erk's branch naming pipeline. Previously, branch names used truncated plan or issue titles directly, resulting in awkward names like `P42-add-objective-context-marker-fallback-02-22-1530`. Now, a Haiku LLM call distills titles into concise 2-4 word slugs, producing readable names like `P42-fix-auth-session-02-22-1530`.

The implementation follows erk's established patterns: `BranchSlugGenerator` mirrors the `CommitMessageGenerator` pattern (concrete class using `PromptExecutor` for testability), `BranchSlugResult` uses the discriminated union success/error pattern, and comprehensive fallback handling ensures no user-visible failures. Five integration points were updated to use the new slug generation: `plan_save.py`, `plan_migrate_to_draft_pr.py`, `setup_impl_from_issue.py`, `one_shot_dispatch.py`, and `submit.py`.

Future agents working on branch naming, LLM-based transformations, or new PromptExecutor consumers will benefit from understanding the slug generation architecture, the five integration points requiring LLM slugs, and the testing patterns for stable branch name assertions.

## Raw Materials

PR #7853

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 6 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 1 |
| Potential tripwires (score 2-3) | 0 |

## Documentation Items

### HIGH Priority

#### 1. BranchSlugGenerator Architecture

**Location:** `docs/learned/architecture/branch-slug-generator.md`
**Action:** CREATE
**Source:** [PR #7853]

**Draft Content:**

```markdown
---
read-when:
  - implementing new LLM-based data transformation
  - working with branch name generation
  - adding PromptExecutor consumers
tripwires: 0
---

# BranchSlugGenerator

LLM-powered branch name slug generation for readable, meaningful branch names.

## Overview

`BranchSlugGenerator` transforms verbose plan/issue titles into concise 2-4 word slugs using a Haiku LLM call. It follows the `CommitMessageGenerator` pattern: a concrete class that accepts a `PromptExecutor` for testability.

## Architecture

### Class Structure

See `src/erk/core/branch_slug_generator.py` for the implementation.

Key components:
- `BranchSlugGenerator`: Main class that accepts `PromptExecutor` via constructor injection
- `BranchSlugResult`: Frozen dataclass discriminated union for success/error handling
- `generate_slug_or_fallback()`: Convenience function that handles failures gracefully

### System Prompt Design

The `BRANCH_SLUG_SYSTEM_PROMPT` constant defines the LLM's behavior:
- Output format: 2-4 hyphenated words, lowercase, maximum 30 characters
- Content strategy: Capture distinctive essence, not generic words
- Verb preference: add, fix, refactor, update, consolidate, extract, migrate
- Filler word removal: Drop "the", "a", "for", "and", "implementation", "plan"

### Post-Processing Pipeline

1. Strip whitespace
2. Strip surrounding quotes and backticks (LLM may wrap output)
3. Run through `sanitize_worktree_name()` as safety net
4. Validate: 2+ hyphenated words
5. Validate: maximum 30 characters
6. Return validated slug or `None` on validation failure

### Fallback Strategy

Three failure modes handled gracefully:
1. **LLM unavailable** (dry-run, network failure): returns raw title
2. **LLM returns error** (rate limit, API failure): returns raw title
3. **LLM returns invalid output** (single word, too long): returns raw title

Downstream `sanitize_worktree_name()` always receives valid input.

## Integration Points

Five branch generation paths use LLM slugs:
- `plan_save.py`: Draft PR branch from plan content
- `plan_migrate_to_draft_pr.py`: Draft PR branch from migration
- `setup_impl_from_issue.py`: Implementation branch from GitHub issue
- `one_shot_dispatch.py`: One-shot submission branch
- `submit.py`: Validation branch name generation

## Testing

Use `FakePromptExecutor` for testing:
- Success path: `FakePromptExecutor(simulated_prompt_output="fix-auth-bug")`
- Failure path: `FakePromptExecutor(simulated_prompt_error="LLM unavailable")`

See `tests/core/test_branch_slug_generator.py` for comprehensive test coverage.

## Related

- [PromptExecutor Gateway](prompt-executor-gateway.md): ABC for LLM inference
- [Discriminated Union Error Handling](discriminated-union-error-handling.md): BranchSlugResult pattern
- [Branch Naming](../erk/branch-naming.md): Overall branch naming conventions
```

---

#### 2. Branch Name Generation Tripwire

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7853]

**Draft Content:**

Add the following tripwire to the erk category tripwires file:

```markdown
## Branch Name Generation

**Trigger:** Before calling `generate_issue_branch_name()` or `generate_draft_pr_branch_name()`

**Warning:** MUST call `generate_slug_or_fallback()` first and pass result to branch name function. Do NOT pass raw `plan.title` or `issue.title` directly.

**Pattern:**
```python
executor = require_prompt_executor(ctx)
slug = generate_slug_or_fallback(executor, title)
branch_name = generate_issue_branch_name(issue_number, slug, timestamp, objective_id=objective_id)
```

**Five affected call sites:**
- `src/erk/cli/commands/exec/scripts/plan_save.py`
- `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`
- `src/erk/cli/commands/one_shot_dispatch.py`
- `src/erk/cli/commands/submit.py`

**Context requirement:** Exec scripts must call `require_prompt_executor(ctx)` to obtain the executor.

**Why this matters:** Skipping LLM slug generation produces valid but non-semantic branch names (e.g., `P42-plan-implement-the-user-auth...` instead of `P42-fix-auth-session`). No exception is thrown, so the bug is silent.
```

---

### MEDIUM Priority

#### 3. PromptExecutor Single-Shot Usage Pattern

**Location:** `docs/learned/architecture/prompt-executor-patterns.md`
**Action:** UPDATE
**Source:** [PR #7853]

**Draft Content:**

Add the following section to the existing prompt executor documentation:

```markdown
## Single-Shot Prompt Usage

For data transformation tasks (slug generation, commit messages), use `execute_prompt()` instead of streaming methods.

### Example: BranchSlugGenerator

See `src/erk/core/branch_slug_generator.py` for the implementation.

Key characteristics:
- Uses `execute_prompt()` for one-shot LLM calls
- Model selection: Haiku for speed/cost balance on transformation tasks
- Error handling: Returns `PromptResult(success, output, error)` discriminated union
- Testing: Use `FakePromptExecutor.simulated_prompt_output` for deterministic assertions

### When to Use execute_prompt()

- Data transformation (title to slug, diff to commit message)
- Structured output extraction
- Classification tasks
- Any task requiring a single LLM response without streaming
```

---

#### 4. Stable Branch Name Test Pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #7853]

**Draft Content:**

Add the following section to the testing documentation:

```markdown
## Stable Branch Name Assertions

### Problem

LLM-generated branch slugs are non-deterministic, breaking assertions like:
```python
assert branch_name == "P42-fix-auth-session-02-22-1530"  # Fails unpredictably
```

### Solution

Configure `FakePromptExecutor` with `simulated_prompt_error` to force fallback to the raw title, making branch names deterministic.

See `tests/commands/submit/conftest.py` for the pattern.

### When to Use

- Any test asserting on branch names generated via `generate_slug_or_fallback()`
- Tests where branch name content matters for assertions

### Alternative for Slug Tests

For tests specifically testing slug generation, use `simulated_prompt_output` with a known deterministic slug:
```python
executor = FakePromptExecutor(simulated_prompt_output="fix-auth-bug")
```
```

---

#### 5. Branch Naming UX Improvement

**Location:** `docs/learned/erk/branch-naming.md`
**Action:** UPDATE
**Source:** [PR #7853]

**Draft Content:**

Add the following section to the existing branch naming documentation:

```markdown
## LLM-Based Slug Generation

### Overview

Branch names now use LLM-generated slugs for improved readability.

### Before and After

| Before | After |
|--------|-------|
| `P42-add-objective-context-marker-fallback-02-22-1530` | `P42-fix-context-marker-02-22-1530` |
| `plnd/plan-implement-the-user-auth-module-01-15` | `plnd/fix-auth-session-01-15` |

### Impact

- Improved git log readability
- Easier stack navigation with Graphite
- Better PR discovery in GitHub

### Architecture

See `docs/learned/architecture/branch-slug-generator.md` for implementation details.

### Fallback Behavior

If the LLM is unavailable or returns invalid output, the system falls back to the raw title. The downstream `sanitize_worktree_name()` ensures all branch names are valid regardless of source.
```

---

### LOW Priority

#### 6. FakePromptExecutor Configuration Parameters

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #7853]

**Draft Content:**

Add to the fake documentation section:

```markdown
### FakePromptExecutor Configuration

`FakePromptExecutor` supports two parameters for controlling `execute_prompt()` behavior:

- `simulated_prompt_output`: Output to return on success (default: "Test Title\n\nTest body")
- `simulated_prompt_error`: Error to return on failure (forces fallback behavior)

See `tests/fakes/prompt_executor.py` for the implementation.

**Usage patterns:**
- Success testing: `FakePromptExecutor(simulated_prompt_output="fix-auth-bug")`
- Fallback testing: `FakePromptExecutor(simulated_prompt_error="LLM unavailable")`
- Stable assertions: Use `simulated_prompt_error` when branch names must be deterministic
```

---

## Contradiction Resolutions

**No contradictions detected.**

The existing branch naming documentation (`docs/learned/erk/branch-naming.md`) and the new LLM-based slug generation are complementary:

- **Existing approach**: Mechanical sanitization via `sanitize_worktree_name()` (deterministic, fast, no external dependencies)
- **New approach**: LLM-based generation via `BranchSlugGenerator` (semantic, meaningful, requires PromptExecutor)
- **Integration**: BranchSlugGenerator uses PromptExecutor and falls back to mechanical sanitization on failure (defense-in-depth)

## Stale Documentation Cleanup

**No stale documentation detected.**

All file references in reviewed documentation were verified and are valid.

## Code Changes (SHOULD_BE_CODE items)

The following items were identified as belonging in source code rather than learned documentation:

### 1. require_prompt_executor() Docstring

**Location:** Source code (wherever `require_prompt_executor()` is defined)
**Action:** CODE_CHANGE

Add docstring explaining:
- Context helper that returns `PromptExecutor` from context
- When to use: Any exec script needing LLM inference
- Error handling: Raises if prompt executor not available in context
- Testing: Inject `FakePromptExecutor` via `context_for_test(prompt_executor=...)`

### 2. generate_branch_name() Docstring

**Location:** `src/erk/cli/commands/one_shot_dispatch.py`
**Action:** CODE_CHANGE

Update docstring to explain the `prompt_executor: PromptExecutor | None` parameter:
- When None, skips LLM slug generation (dry-run mode, tests)
- Dry-run handling: Passes `prompt_executor=None` to skip LLM call
- Live execution: Uses `ctx.prompt_executor` for LLM slug generation

## Prevention Insights

**No session analysis available** (`session_analysis_paths: []`), so no implementation errors or failed approaches could be identified.

Limitation: Without session data, we cannot identify:
- Patterns discovered during implementation
- Prevention insights (error patterns and failed approaches)
- External lookups indicating missing documentation
- Evolution of understanding during development

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Branch Name Generation MUST Use LLM Slugs

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before calling `generate_issue_branch_name()` or `generate_draft_pr_branch_name()`

**Warning:** MUST call `generate_slug_or_fallback()` first and pass result to branch name function. Do NOT pass raw `plan.title` or `issue.title` directly. Pattern: `slug = generate_slug_or_fallback(executor, title)`. Five affected call sites: `plan_save.py`, `plan_migrate_to_draft_pr.py`, `setup_impl_from_issue.py`, `one_shot_dispatch.py`, `submit.py`.

**Target doc:** `docs/learned/erk/tripwires.md`

This tripwire is warranted because:
- **Non-obvious**: The function signatures of `generate_issue_branch_name()` and `generate_draft_pr_branch_name()` don't indicate that slug generation is required first
- **Cross-cutting**: Applies to five distinct workflows across the codebase
- **Silent failure**: Skipping slug generation produces valid but non-semantic branch names; no exception is thrown, so the UX degradation is subtle and easily missed

## Potential Tripwires

**No items with score 2-3.**

All cross-cutting concerns either scored high enough for tripwire status (score 6) or were implementation details not requiring tripwire documentation.

## Open Questions

These questions emerged from the implementation but remain unanswered:

1. **Performance**: What's the latency impact of adding an LLM call to branch creation?
2. **Rate limiting**: How does the system handle Claude API rate limits during high-frequency branch creation?
3. **Caching**: Should identical titles produce cached slugs to avoid redundant LLM calls?
4. **User override**: Should users be able to provide a custom slug via CLI flag?
5. **Slug uniqueness**: Can two different titles produce the same slug?
6. **Dry-run behavior**: Should dry-run mode show what the LLM would generate?

Consider addressing these in the architecture documentation or as follow-up investigations.
