# Documentation Plan: Make pr-feedback-classifier faster with combined PR feedback command

## Context

This PR (#8252) implemented a significant performance optimization for the `pr-feedback-classifier` skill by consolidating three separate subprocess calls into a single `erk exec get-pr-feedback` command. The original workflow made three sequential exec calls (`get-pr-review-comments`, `get-pr-discussion-comments`, and a PR lookup), each spawning a new subprocess with its own GitHub API calls. The consolidated command performs a single PR lookup, then fetches review threads and discussion comments in parallel using `ThreadPoolExecutor`. This reduced total execution time from 15-25 seconds to 5-8 seconds.

The implementation sessions revealed several important architectural patterns. Most notably, the introduction of the `NonIdealState.ensure()` pattern eliminates repetitive `_ensure_*` helper functions in exec scripts by providing a method-based API that raises `NonIdealStateError`. This exception is caught by a `@handle_non_ideal_exit` decorator that converts it to JSON output. Additionally, the sessions uncovered a critical type system quirk: `ty` does not narrow union types through Protocol-based `isinstance` checks or after `NoReturn` function calls, requiring explicit `assert not isinstance()` statements.

A future agent implementing similar exec commands or refactoring existing ones would benefit from understanding: (1) when and how to use `ThreadPoolExecutor` for parallel I/O, (2) the `NonIdealState.ensure()` pattern for eliminating helper function boilerplate, (3) type narrowing requirements after `NoReturn` calls, and (4) model selection criteria for skills (haiku wrote temporary Python scripts instead of reasoning, forcing a reversion to sonnet).

## Raw Materials

See associated PR #8252 and session analysis files.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 17    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 8     |

## Documentation Items

### HIGH Priority

#### 1. NonIdealState.ensure() pattern

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [Impl] session-952a205d, session-165f1287, [PR #8252]

**Draft Content:**

```markdown
## NonIdealState.ensure() Pattern

### Pattern Overview

When exec scripts handle discriminated unions with non-ideal states, use the `.ensure()` method
pattern to eliminate repetitive `_ensure_*` helper functions.

### How It Works

1. Each non-ideal state class implements `ensure() -> NoReturn` that raises `NonIdealStateError(self)`
2. Ideal state classes implement `ensure() -> Self` that returns `self`
3. Exec scripts use `@handle_non_ideal_exit` decorator to catch `NonIdealStateError` and convert to JSON
4. After calling `.ensure()`, add explicit `assert not isinstance(var, ErrorType)` for ty type narrowing

### When to Use

Use this pattern when:
- An exec script checks multiple discriminated union results
- You see repetitive `_ensure_*` helper functions calling `exit_with_error`

See `packages/erk-shared/src/erk_shared/non_ideal_state.py` for the Protocol definition.
See `src/erk/cli/output/script_output.py` for the `@handle_non_ideal_exit` decorator.
```

---

#### 2. Protocol isinstance checks don't narrow types

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-165f1287-part2

**Draft Content:**

```markdown
## Protocol isinstance Checks

**Trigger:** Before using isinstance(obj, Protocol) for type narrowing

**Warning:** Protocol checks don't narrow union types. Use isinstance(obj, ConcreteClass) instead.
After NoReturn calls, add explicit `assert not isinstance(obj, ErrorType)`.

### Why This Matters

When you write:
```python
result: str | BranchDetectionFailed = get_branch()
if isinstance(result, BranchDetectionFailed):
    result.ensure()  # NoReturn
# ty still sees result as str | BranchDetectionFailed here
```

The type checker doesn't narrow through:
- Protocol-based isinstance checks (isinstance(obj, NonIdealState))
- NoReturn function calls in conditional branches

### Correct Pattern

```python
if isinstance(result, BranchDetectionFailed):
    result.ensure()
assert not isinstance(result, BranchDetectionFailed)  # Explicit narrowing
# ty now knows result is str
```
```

---

#### 3. ThreadPoolExecutor for parallel I/O in exec scripts

**Location:** `docs/learned/architecture/parallel-io-pattern.md`
**Action:** CREATE
**Source:** [Impl] diff analysis, [PR #8252]

**Draft Content:**

```markdown
---
title: Parallel I/O with ThreadPoolExecutor
read-when:
  - fetching multiple independent API resources in exec scripts
  - consolidating multiple sequential subprocess calls into one
tripwires: 1
---

# Parallel I/O with ThreadPoolExecutor

## When to Use

Use ThreadPoolExecutor when an exec script needs to fetch multiple independent resources
from external APIs (GitHub, network services). This is the first and canonical pattern
for subprocess-level parallelism in erk.

## Pattern

See `src/erk/cli/commands/exec/scripts/get_pr_feedback.py` for the reference implementation
that fetches review threads and discussion comments in parallel.

Key elements:
- Use `with ThreadPoolExecutor(max_workers=N)` context manager
- Submit all independent operations via `executor.submit()`
- Collect results via `.result()` after all submissions
- Handle errors from either future appropriately

## Contrast with Sequential

The consolidated get-pr-feedback command reduced 3 subprocess calls to 1, and parallel
fetching within that single subprocess provides additional speedup. Total improvement:
15-25s -> 5-8s (67% reduction from consolidation, additional 2x from parallelism).

## When NOT to Use

- Don't parallelize operations with dependencies
- Don't use for CPU-bound work (use ProcessPoolExecutor instead)
- Consider if error handling complexity outweighs performance gains
```

---

#### 4. Assert after NoReturn for ty type narrowing

**Location:** `docs/learned/testing/type-narrowing-patterns.md`
**Action:** CREATE
**Source:** [Impl] session-165f1287-part2, [PR #8252] bot comments

**Draft Content:**

```markdown
---
title: Type Narrowing After NoReturn
read-when:
  - using discriminated unions with NoReturn error handlers
  - seeing ty possibly-missing-attribute errors after ensure() calls
tripwires: 1
---

# Type Narrowing After NoReturn

## The Problem

ty doesn't automatically narrow union types after calling `NoReturn` functions:

```python
if isinstance(result, ErrorType):
    result.ensure()  # -> NoReturn
# ty still thinks result could be ErrorType here
```

## The Solution

Add explicit assertions immediately after NoReturn calls:

```python
if isinstance(result, ErrorType):
    result.ensure()
assert not isinstance(result, ErrorType)
```

## Why the Bot Flags This

The pr-feedback-classifier bot may flag `assert not isinstance()` after NoReturn
as "unreachable assertion" - this is a false positive. The assertion is required
for ty type narrowing and is correct.

## Related

See `docs/learned/architecture/discriminated-union-error-handling.md` for the
broader pattern of using `.ensure()` methods on discriminated unions.
```

---

#### 5. RuntimeError from gateways: defensive handling vs anti-pattern

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [PR #8252] bot comments

**Draft Content:**

```markdown
## Gateway RuntimeError Handling

### Legitimate Pattern

Catching RuntimeError from gateway methods and converting to exit_with_error IS correct:

```python
try:
    result = gateway.some_operation()
except RuntimeError as e:
    exit_with_error("gateway_error", str(e))
```

Gateway methods (like `execute_gh_command_with_retry`) may raise RuntimeError for
infrastructure failures. Exec scripts should catch and convert to JSON error output.

### Anti-Pattern (Still Forbidden)

What remains forbidden is RAISING RuntimeError for CLI failures:

```python
# WRONG - don't raise RuntimeError for expected error cases
if not file.exists():
    raise RuntimeError(f"File not found: {file}")
```

Use discriminated unions and exit_with_error instead.
```

---

#### 6. get-pr-feedback exec command

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [Impl] diff analysis

**Draft Content:**

```markdown
## PR Operations

### get-pr-feedback

Consolidates review thread and discussion comment fetching into a single command.

**Usage:**
- `erk exec get-pr-feedback` - auto-detect current branch's PR
- `erk exec get-pr-feedback --pr 123` - explicit PR number
- `erk exec get-pr-feedback --include-resolved` - include resolved threads

**Output:** JSON with `pr_number`, `review_threads`, `discussion_comments`

**Replaces:** Sequential calls to `get-pr-review-comments` + `get-pr-discussion-comments` + PR lookup.

**Performance:** 3 subprocess calls -> 1, with parallel internal fetching. 67% subprocess overhead reduction.

See `src/erk/cli/commands/exec/scripts/get_pr_feedback.py` for implementation.
```

---

### MEDIUM Priority

#### 7. pr-feedback-classifier performance optimization

**Location:** `.claude/skills/pr-feedback-classifier/SKILL.md`
**Action:** UPDATE
**Source:** [Impl] session-c3f75006, [PR #8252]

**Draft Content:**

```markdown
## Performance Notes

This skill was optimized in PR #8252:
- Consolidated from 3 exec calls to 1 (`erk exec get-pr-feedback`)
- Total time reduced from 15-25s to 5-8s
- Model: Uses sonnet (not haiku - see below)

### Why Sonnet, Not Haiku

Testing showed haiku wrote temporary Python scripts to classify JSON data instead
of reasoning directly. This polluted /tmp and added unnecessary complexity.
The "Critical Constraints" section explicitly forbids code file generation.

If considering haiku for performance, first verify in test environment that it
doesn't exhibit code-generation behavior.
```

---

#### 8. LBYL ensure helpers pattern for exec scripts

**Location:** `docs/learned/cli/exec-error-handling.md`
**Action:** CREATE
**Source:** [Impl] diff analysis

**Draft Content:**

```markdown
---
title: Exec Script Error Handling
read-when:
  - creating new exec scripts
  - handling discriminated unions in exec scripts
tripwires: 1
---

# Exec Script Error Handling

## Two Error Handling Systems

Erk has two parallel systems for handling NonIdealState errors:

| Context | Handler | Output | Exit Code |
|---------|---------|--------|-----------|
| Exec scripts | exit_with_error() | JSON | 0 |
| CLI commands | EnsureIdeal | Colored text | 1 |

## Modern Pattern: .ensure() with Decorator

Prefer using `@handle_non_ideal_exit` decorator with `.ensure()` calls:

```python
@handle_non_ideal_exit
def my_exec_command(...):
    result = some_operation()
    if isinstance(result, SomeError):
        result.ensure()  # Raises NonIdealStateError
    # Continue with ideal state
```

See `src/erk/cli/output/script_output.py` for decorator implementation.

## Legacy Pattern: _ensure_* Helpers

Older exec scripts used helper functions:

```python
def _ensure_result(result):
    if isinstance(result, SomeError):
        exit_with_error(result.error_type, result.message)
    return result
```

New code should use the `.ensure()` pattern instead.
```

---

#### 9. Exec script testing gold standard

**Location:** `docs/learned/testing/exec-script-testing-exemplar.md`
**Action:** CREATE
**Source:** [PR #8252] bot comments

**Draft Content:**

```markdown
---
title: Exec Script Testing Exemplar
read-when:
  - writing tests for new exec scripts
  - reviewing exec script test coverage
---

# Exec Script Testing Exemplar

The `get_pr_feedback.py` test suite demonstrates exemplary coverage for exec scripts.

## Coverage Categories

See `tests/unit/cli/commands/exec/scripts/test_get_pr_feedback.py` for reference.

**Success paths:**
- With explicit PR number
- Auto-detect branch
- Empty results
- Include/filter resolved threads

**Error paths:**
- PR not found
- No branch detected

**JSON structure validation:**
- All expected top-level keys
- Nested structures (threads, comments)

## Testing Guidelines

- Use fake-driven testing (FakeGitHub, FakeGit, etc.)
- Cover both success and error paths
- Validate JSON output structure, not just status
- Test flag combinations (--include-resolved, --pr)
```

---

#### 10. GitHub API quirk: empty thread IDs

**Location:** `docs/learned/integrations/github-api-quirks.md`
**Action:** UPDATE
**Source:** [Impl] diff analysis

**Draft Content:**

```markdown
## Empty Thread IDs in GraphQL Response

**Issue:** Some PR review threads returned by GraphQL have empty or null IDs.

**Workaround:** Always filter threads before processing:
```python
valid_threads = [t for t in threads if t.id]
```

**Impact:** Without filtering, malformed JSON output or crashes when accessing thread.id

**Source:** Discovered in get_pr_feedback.py implementation.
```

---

#### 11. Skill model selection guidance

**Location:** `docs/learned/commands/skill-model-selection.md`
**Action:** CREATE
**Source:** [Impl] session-c3f75006

**Draft Content:**

```markdown
---
title: Skill Model Selection
read-when:
  - creating new skills
  - optimizing skill performance
  - debugging unexpected skill behavior
tripwires: 1
---

# Skill Model Selection

## Model Tiers

| Model | Use When | Avoid When |
|-------|----------|------------|
| opus | Complex reasoning, multi-step tasks | Simple classification |
| sonnet | Structured data classification, code analysis | Simple lookups |
| haiku | Fast lookups, simple transformations | Pure reasoning tasks |

## Case Study: pr-feedback-classifier

Initial optimization attempted to use haiku for faster classification.

**What happened:** Haiku wrote temporary Python scripts (`/tmp/classify_*.py`) to
process JSON data instead of reasoning directly.

**Resolution:**
1. Reverted to sonnet
2. Added explicit "DO NOT write code files" constraint

## Testing Model Changes

Before downgrading a skill's model tier:
1. Run in test environment
2. Check /tmp for spurious files
3. Verify output quality matches expectations
4. Look for code-generation behavior
```

---

#### 12. Stacked plan PR workflow

**Location:** `docs/learned/planning/`
**Action:** UPDATE
**Source:** [Impl] session-165f1287-part1

**Draft Content:**

```markdown
## Stacked Plan PR Lifecycle

When a base PR receives review feedback, create a stacked plan PR to address it.

### Workflow

1. Base PR (e.g., #8252) receives review comments
2. Create stacked branch: `plnd/add-ensure-nonidealstate-...`
3. Add plan commit with `.erk/impl-context/plan.md`
4. Add cleanup commit removing `.erk/impl-context/`
5. Implement changes in same branch
6. Resolve original PR's review thread after implementation

### Detecting Pending Work

A cleanup commit (removing impl-context) WITHOUT subsequent implementation commits
indicates work is still pending. Don't try to run `/erk:pr-address` on such branches.

### Cross-Branch Inspection

Use `git show origin/branch:path` to inspect files without switching worktrees.
Use parent commit to see plan file that was removed by cleanup commit.
```

---

#### 13. Test helpers follow production rules

**Location:** `docs/learned/testing/test-helper-patterns.md`
**Action:** CREATE
**Source:** [PR #8252] bot comments

**Draft Content:**

```markdown
---
title: Test Helper Patterns
read-when:
  - writing test helper functions
  - seeing bot complaints about default parameters in tests
tripwires: 1
---

# Test Helper Patterns

## Production Rules Apply

Test helpers MUST follow the same dignified-python rules as production code:
- No default parameter values
- Keyword-only arguments after *
- LBYL patterns

## Why the Bot Complains

The pr-feedback-classifier bot flagged multiple test helpers for having default
parameters. Test helpers are NOT exempt from coding standards.

## Correct Pattern

```python
def make_test_thread(
    *,
    id: str,
    is_resolved: bool,
    path: str,
    line: int,
):
    ...
```

NOT:
```python
def make_test_thread(id: str = "thread-1", is_resolved: bool = False):  # WRONG
    ...
```
```

---

### LOW Priority

#### 14. Cross-branch file inspection pattern

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-165f1287-part1

**Draft Content:**

```markdown
## Cross-Branch File Inspection

**Trigger:** Before switching worktrees to inspect file contents

**Warning:** Use `git show origin/branch:path` for read-only inspection. Avoids worktree
switching overhead.

**Example:**
```bash
git show origin/plnd/my-feature:src/erk/config.py
```

This is faster and doesn't affect your working directory state.
```

---

#### 15. Worktree discovery commands

**Location:** `docs/learned/erk/worktrees.md`
**Action:** UPDATE
**Source:** [Impl] session-165f1287-part1

**Draft Content:**

```markdown
## Finding Worktrees by Branch Name

To find which worktree contains a specific branch:

```bash
for slot in worktrees/erk-slot-*/; do
    git -C "$slot" branch --show-current | grep pattern && echo "$slot"
done
```

Or more concisely:
```bash
for slot in worktrees/*/; do
    branch=$(git -C "$slot" branch --show-current 2>/dev/null)
    [[ "$branch" == *pattern* ]] && echo "$slot: $branch"
done
```
```

---

#### 16. Deferred doc fixes tracking

**Location:** `docs/learned/documentation/deferred-fixes.md`
**Action:** CREATE
**Source:** [PR #8252] gap analysis

**Draft Content:**

```markdown
---
title: Deferred Documentation Fixes
read-when:
  - discovering doc inaccuracies during PR review
  - triaging documentation debt
---

# Deferred Documentation Fixes

## When to Defer

During PR review, you may discover documentation inaccuracies that are OUT OF SCOPE
for the current PR. Track these for future fixing rather than expanding PR scope.

## Tracking Pattern

In the PR's gap analysis or learn plan, add a "Stale Documentation Actions" section:

| Doc | Issue | Action | Rationale |
|-----|-------|--------|-----------|
| path/to/doc.md | Description of inaccuracy | UPDATE_REFERENCES | Out of scope for PR #N |

## Current Deferred Fixes

| Doc | Issue | Discovered In |
|-----|-------|---------------|
| docs/learned/tui/status-indicators.md | Line 76: incomplete stage detection condition | PR #8252 |
```

---

#### 17. @handle_non_ideal_exit decorator pattern

**Location:** `docs/learned/architecture/` or `docs/learned/cli/`
**Action:** CREATE
**Source:** [Impl] session-952a205d-part2

**Draft Content:**

```markdown
---
title: handle_non_ideal_exit Decorator
read-when:
  - creating exec scripts that use NonIdealState
  - refactoring exec scripts to use .ensure() pattern
---

# @handle_non_ideal_exit Decorator

## Purpose

Centralizes non-ideal state error handling for exec scripts. Catches
`NonIdealStateError` and converts to JSON error output.

## Usage

```python
@handle_non_ideal_exit
def my_exec_script(...):
    result = some_operation()
    if isinstance(result, SomeErrorType):
        result.ensure()  # Raises NonIdealStateError
    # ... continue with ideal state
```

See `src/erk/cli/output/script_output.py` for implementation.

## Relationship to .ensure()

This decorator is the companion to the `.ensure()` method on NonIdealState classes.
Together they replace the older pattern of `_ensure_*` helper functions calling
`exit_with_error()` directly.
```

---

## Contradiction Resolutions

No contradictions found. The existing documentation checker confirmed that all referenced files exist and no conflicting guidance was detected.

## Stale Documentation Cleanup

One pre-existing inaccuracy was identified but is out of scope for this PR:

### 1. Status indicators incomplete condition

**Location:** `docs/learned/tui/status-indicators.md`
**Action:** DEFER
**Phantom References:** Line 76 has incomplete stage detection condition (missing uppercase REVIEW guard)
**Cleanup Instructions:** Track for future fix. Document in deferred-fixes.md.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Type narrowing with Protocols

**What happened:** AttributeError accessing properties on error objects after isinstance(obj, Protocol) check.
**Root cause:** ty doesn't narrow union types through Protocol checks even when checked branch calls NoReturn.
**Prevention:** Use concrete class isinstance checks + explicit assertions after NoReturn calls.
**Recommendation:** TRIPWIRE

### 2. NonIdealState handling boilerplate

**What happened:** Four identical _ensure_* helper functions duplicating error-handling logic across get_pr_feedback.py.
**Root cause:** No standard pattern for discriminated union error handling in exec scripts.
**Prevention:** Add .ensure() method to NonIdealState classes that raises NonIdealStateError; use @handle_non_ideal_exit decorator.
**Recommendation:** TRIPWIRE

### 3. Model selection for reasoning tasks

**What happened:** Haiku wrote temporary Python scripts (`/tmp/classify_*.py`) instead of reasoning directly when classifying PR feedback.
**Root cause:** Smaller models lack reasoning capacity for structured data classification; haiku "thought" it needed code to process JSON.
**Prevention:** Use sonnet or opus for pure reasoning tasks. Add explicit "DO NOT write code files" constraints when using smaller models.
**Recommendation:** ADD_TO_DOC

### 4. Plan PR workflow confusion

**What happened:** Agent uncertain whether to run /erk:pr-address or implement changes directly on stacked plan branch.
**Root cause:** Stacked plan PR lifecycle not documented (plan commit -> cleanup commit -> implementation).
**Prevention:** Document that cleanup commit without implementation commits = work is pending.
**Recommendation:** ADD_TO_DOC

### 5. Type narrowing after NoReturn

**What happened:** ty reports "possibly-missing-attribute" after calling .ensure() (NoReturn function).
**Root cause:** ty doesn't automatically narrow union types after NoReturn paths.
**Prevention:** Add explicit `assert not isinstance(var, ErrorType)` after NoReturn calls.
**Recommendation:** TRIPWIRE

### 6. Test helpers default parameters

**What happened:** Bot repeatedly flagged default parameter values in test helpers as violations.
**Root cause:** Confusion about whether test helpers follow same rules as production code.
**Prevention:** Clarify in testing docs that test helpers must follow dignified-python rules.
**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Protocol isinstance checks don't narrow types

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using isinstance(obj, Protocol) for type narrowing
**Warning:** Protocol checks don't narrow union types. Use isinstance(obj, ConcreteClass) instead. After NoReturn calls, add explicit `assert not isinstance(obj, ErrorType)`.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is highly tripwire-worthy because the failure is silent at type-check time but causes AttributeError at runtime. The pattern of checking isinstance(obj, Protocol) and then calling a NoReturn function looks correct but doesn't provide the expected type narrowing. Every exec script using discriminated unions is affected.

### 2. NonIdealState.ensure() pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** When handling discriminated unions with non-ideal states
**Warning:** Add .ensure() method that returns self for ideal states and raises NonIdealStateError for non-ideal states. Eliminates _ensure_* helper boilerplate.
**Target doc:** `docs/learned/architecture/tripwires.md`

This pattern affects all 12 exec scripts that currently use `exit_with_error(result.error_type, result.message)`. The .ensure() pattern with @handle_non_ideal_exit decorator provides a cleaner, more consistent approach. Without this tripwire, new exec scripts will reinvent the _ensure_* helper pattern.

### 3. Assert after NoReturn for type narrowing

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After calling .ensure() or other NoReturn functions on discriminated unions
**Warning:** Add explicit `assert not isinstance(var, ErrorType)` to help ty narrow the type. ty doesn't automatically narrow through NoReturn paths.
**Target doc:** `docs/learned/testing/tripwires.md`

Confusing for reviewers because the pr-feedback-classifier bot flags these assertions as "unreachable" - a false positive. The assertions are required for correct type narrowing with ty.

### 4. ThreadPoolExecutor for parallel I/O

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When fetching multiple independent API resources in exec scripts
**Warning:** Use ThreadPoolExecutor with max_workers=N to parallelize independent calls. Example: get_pr_feedback.py fetches review threads + discussion comments in parallel.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is the first use of subprocess-level parallelism in erk's codebase. Future exec scripts that fetch multiple independent resources should consider this pattern for performance.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Cross-branch file inspection

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Use `git show origin/branch:path` pattern appeared multiple times in session. Useful but not critical - worktree switching works, just slower.

### 2. Worktree discovery pattern

**Score:** 2/10 (Cross-cutting +2)
**Notes:** Pattern for finding worktrees by branch name is useful but could be a helper command instead of a tripwire.

### 3. Null ID filtering for GitHub threads

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Always filter with `if t.id` before processing. Specific to GitHub GraphQL API quirk.

### 4. RuntimeError from gateways

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Catching RuntimeError from gateways is CORRECT; raising it for CLI failures is anti-pattern. Distinction is subtle.

### 5. Plan PR lifecycle

**Score:** 2/10 (Non-obvious +2)
**Notes:** Cleanup commit without implementation commits = work is pending. Specific to plan PR workflow.

### 6. Haiku writing Python scripts

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Smaller models may resort to code generation instead of pure reasoning. Test before using haiku for classification tasks.

### 7. Test helpers no defaults

**Score:** 2/10 (Cross-cutting +2)
**Notes:** Test helpers follow same rules as production code. Bot flagged 7 threads about this.

### 8. Consolidated exec commands

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** When skills make 3+ sequential subprocess calls, consolidate into single command. Performance pattern.
