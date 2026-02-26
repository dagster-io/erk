# Document testing infrastructure gaps from backend consolidation

## Context

PR #8236 represents a comprehensive documentation synchronization effort, updating 64 files to align with three major architectural changes: CLI consolidation (moving `erk plan` subcommands under `erk pr`), backend consolidation (removing dual backend architecture in favor of unified `PlannedPRBackend`), and branch naming migration (from `P{issue}-*` prefix to `plnd/*` prefix with `plan-ref.json` as source of truth).

While the PR itself contains no new code or features, the implementation sessions revealed significant gaps in testing infrastructure documentation and PR operations workflow patterns. Seven separate PR review violations caught the same constructor signature error, indicating that agents consistently struggle with test setup patterns that have evolved alongside the backend consolidation. The sessions also demonstrated mature integration between plan mode and PR operations, with clean hook intervention, marker-based signaling, and batch resolution patterns that deserve documentation.

The highest-value documentation opportunities center on preventing repeated test infrastructure mistakes. The `PlannedPRBackend` constructor signature change from single-arg to 3-arg has caused numerous failures, and the `FakeGitHub` mutation tracking API lacks a comprehensive reference. These gaps create friction for agents implementing tests that interact with the plan backend.

## Raw Materials

Materials from PR #8236 and implementation sessions 5361cc7f, b6196a52, and b852e7e2.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 16    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 5     |

## Documentation Items

### HIGH Priority

#### 1. PlannedPRBackend Constructor Signature Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
## PlannedPRBackend Constructor Signature

**Trigger:** Creating PlannedPRBackend in tests

**Warning:** Use 3-arg constructor: `PlannedPRBackend(github, github_issues, time=FakeTime())`, not single-arg `PlannedPRBackend(fake_github)`

The constructor signature changed during backend consolidation. The outdated single-arg pattern appears in older test examples but is no longer valid. Always provide all three arguments explicitly.

See `src/erk/planned_pr_backend.py` for the current constructor signature.
```

---

#### 2. FakeGitHub Mutation Tracking API Reference

**Location:** `docs/learned/testing/fake-github-api.md`
**Action:** CREATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
---
read-when: writing tests that verify GitHub mutations, checking test assertions for PR updates, debugging test failures involving FakeGitHub
tripwires: 2
---

# FakeGitHub Mutation Tracking API

Reference for mutation tracking properties on FakeGitHub used in test assertions.

## PR Mutations

<!-- Source: tests/fake/fake_github.py -->

- `updated_pr_bodies`: List of `(pr_number, body)` tuples for PR body updates
- `updated_pr_titles`: List of `(pr_number, title)` tuples for PR title updates
- `created_prs`: List of PR creation records

**Important:** The property is `updated_pr_bodies`, not `updated_prs`. The naming follows the pattern `updated_{field}` for specific field updates.

## Issue Mutations

- `closed_issues`: Set of issue numbers that were closed
- `created_issues`: List of issue creation records

## Assertion Patterns

See `tests/test_utils/plan_helpers.py` for test setup patterns that demonstrate these assertions.

For comprehensive backend testing patterns, see [Backend Testing Composition](backend-testing-composition.md).
```

---

#### 3. context_for_test() Parameter Naming Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
## context_for_test() Parameter Naming

**Trigger:** Using context_for_test() in tests

**Warning:** Parameter is `plan_store` (not `plan_backend`)

The parameter naming follows the naming convention established during backend consolidation. Despite the backend being named `PlannedPRBackend`, the context factory parameter uses `plan_store` for historical reasons.

See `tests/conftest.py` for the `context_for_test()` signature.
```

---

#### 4. erk exec update-pr-description Silent Failure

**Location:** `docs/learned/pr-operations/command-error-handling.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: debugging erk exec command failures, troubleshooting PR operations, investigating silent command failures
tripwires: 1
---

# Command Error Handling Patterns

Patterns for detecting and handling errors in erk exec commands.

## Silent Failure Detection

Some erk exec commands can fail silently without stderr output.

### erk exec update-pr-description

**Expected behavior:** Returns JSON with `title` and `body` keys on success.

**Silent failure indicator:** Empty stdout with no error message.

**Prevention:**
1. Always check for non-empty output from commands returning JSON
2. If stdout is empty, treat as failure and investigate separately
3. Do not assume success based on lack of error message

This pattern was discovered in session b852e7e2 where the command failed silently twice without investigation.
```

---

### MEDIUM Priority

#### 5. PR Address Workflow with Plan Mode

**Location:** `docs/learned/pr-operations/plan-mode-integration.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: using /erk:pr-address command, integrating plan mode with PR operations, understanding hook-based workflow control
tripwires: 0
---

# PR Operations and Plan Mode Integration

How PR address workflows integrate with plan mode for controlled implementation.

## Workflow Overview

When `/erk:pr-address` results in a plan:

1. **Plan Creation**: Agent analyzes review comments and creates plan file
2. **Hook Intervention**: ExitPlanMode is intercepted by `exit-plan-mode-hook`
3. **User Decision**: Hook prompts with options: Create plan PR / Skip PR and implement / View/Edit
4. **Marker-Based Signaling**: If "implement now" selected, creates `exit-plan-mode-hook.implement-now` marker
5. **Smooth Transition**: Agent proceeds directly to implementation without PR creation

## ExitPlanMode Hook Requirements

Before calling ExitPlanMode:
1. Read and display the plan file to user
2. Use AskUserQuestion with structured options
3. Create appropriate marker based on user choice

See `.claude/hooks/exit-plan-mode-hook.py` for hook implementation.
```

---

#### 6. Task Tool vs Skill Invocation for Subagents

**Location:** `docs/learned/commands/subagent-isolation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: creating commands that invoke classifier skills, using --print mode in commands, implementing subagent workflows
tripwires: 1
---

# Subagent Isolation Patterns

Why Task tool is required for proper subagent isolation in certain contexts.

## The Problem

The `context: fork` metadata in skill definitions suggests isolation, but this doesn't create true subagent isolation in `--print` mode contexts.

## The Solution

Use explicit `Task` tool calls instead of `Skill` invocation when:
- Command uses `--print` mode
- Classifier or analyzer needs to run in isolation
- Results need to be captured without affecting main conversation

## Example: pr-feedback-classifier

The `/erk:pr-address` instructions explicitly require Task tool for the classifier:

```
# Correct - true isolation
Task tool with pr-feedback-classifier prompt

# Incorrect - shares context despite metadata
Skill invocation of pr-feedback-classifier
```

This pattern is demonstrated in all three implementation sessions for PR #8236.
```

---

#### 7. Click Callback Parameter Convention

**Location:** `docs/learned/cli/click-exceptions.md`
**Action:** CREATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
---
read-when: adding @click.pass_obj to CLI commands, fixing parameter convention errors in Click callbacks, reviewing dignified-python false positives
tripwires: 1
---

# Click Callback Exceptions to Parameter Conventions

Exception to keyword-only parameter rule for Click callbacks.

## @click.pass_obj Exception

The dignified-python standard requires keyword-only parameters (`def foo(*, param: T)`). However, `@click.pass_obj` requires a positional context parameter.

**Correct pattern:**
```python
@click.pass_obj
def my_command(ctx, *, verbose: bool):
    ...
```

**Why:** Click injects the context object positionally. The `*` separator comes after the context parameter.

This is a known exception - not a dignified-python violation.
```

---

#### 8. Test Helper Function Naming Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
## Test Helper Function Naming

**Trigger:** Creating plan store in tests

**Warning:** Use `create_plan_store_with_plans()` for test setup, not `create_plan_store()`

The helper function name includes `with_plans` to indicate it initializes with test data. The simpler name `create_plan_store()` does not exist.

See `tests/test_utils/plan_helpers.py` for the function signature.
```

---

#### 9. Outdated Thread Detection

**Location:** `docs/learned/pr-operations/addressing-feedback.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Outdated Thread Handling

Review threads can become outdated when code changes between when the comment was posted and when it's addressed.

### Detection

- `line: null` in thread data indicates the referenced line no longer exists
- Thread may reference code that has already been fixed

### Response Pattern

1. Read the current file state
2. Verify if the issue has already been fixed
3. If fixed: resolve thread with explanatory comment ("This issue was already resolved...")
4. If not fixed: proceed with code changes

### Example

Session 5361cc7f encountered 2/3 threads that were already fixed. Agent correctly:
- Verified current code state before making changes
- Resolved with explanations rather than redundant edits
```

---

### LOW Priority

#### 10. Implement-Now Marker Pattern

**Location:** `docs/learned/planning/plan-mode-markers.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## exit-plan-mode-hook.implement-now

**Purpose:** Signal that PR creation should be skipped and implementation should proceed directly.

**Created by:** Agent after user selects "Skip PR and implement here" option

**Command:**
```bash
erk exec marker create --session-id {id} exit-plan-mode-hook.implement-now
```

**Effect:** Downstream workflows recognize this marker and skip PR creation steps.
```

---

#### 11. Batch Thread Resolution

**Location:** `docs/learned/pr-operations/batch-operations.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Batch Thread Resolution

Use `erk exec resolve-review-threads` with JSON stdin for resolving multiple threads efficiently.

### JSON Format

```json
[
  {
    "thread_id": "PRRT_kwDO...",
    "comment": "Fixed in {commit_sha} - description of fix"
  },
  {
    "thread_id": "PRRT_kwDO...",
    "comment": "Fixed in {commit_sha} - description of fix"
  }
]
```

### Benefits

- Single API call instead of multiple individual calls
- 50% reduction in API round trips for 2 threads
- Atomic resolution with consistent timestamps
```

---

#### 12. Line Number References in Docs

**Location:** `docs/learned/documentation/source-pointers.md`
**Action:** UPDATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
## NEVER Use Line Number Ranges

**Anti-pattern:**
```markdown
See lines 84-86 of tests/test_utils/plan_helpers.py
```

**Why:** Line numbers drift with every edit. Even a single-line addition anywhere above shifts all subsequent line numbers, creating silent documentation rot.

**Correct pattern:**
```markdown
<!-- Source: tests/test_utils/plan_helpers.py, create_plan_store_with_plans -->

See `create_plan_store_with_plans` in `tests/test_utils/plan_helpers.py` for the full signature.
```

Use method/function names instead of line numbers. The HTML comment enables staleness detection; the prose enables agent navigation.
```

---

#### 13. Verbatim Source Code Copies

**Location:** `docs/learned/documentation/source-pointers.md`
**Action:** UPDATE
**Source:** [PR #8236]

**Draft Content:**

```markdown
## Source Pointer Format (Reinforcement)

The two-part format is mandatory for all code references:

1. **HTML comment** - Machine-readable for staleness detection
2. **Prose reference** - Human-readable for agent navigation

### Example Application (from PR #8236)

**Before (anti-pattern):**
```python
def create_plan_store_with_plans(
    github: FakeGitHub,
    github_issues: FakeGitHubIssues,
    time: FakeTime | None = None,
) -> PlannedPRBackend:
```

**After (correct):**
```markdown
<!-- Source: tests/test_utils/plan_helpers.py, create_plan_store_with_plans -->

See `create_plan_store_with_plans` in `tests/test_utils/plan_helpers.py` for the full signature.
```

This transformation was applied consistently across sessions b6196a52 and b852e7e2.
```

---

#### 14. ExitPlanMode Hook Block

**Location:** `docs/learned/planning/plan-mode-exit-flow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Hook Requirements Before ExitPlanMode

The `exit-plan-mode-hook` will block if ExitPlanMode is called without proper preparation:

### Required Steps

1. **Read the plan file** - Load the plan content to display to user
2. **Display to user** - Show the plan summary or key points
3. **Use AskUserQuestion** - Present structured options:
   - Create plan PR
   - Skip PR and implement here
   - View/Edit plan

### Error Pattern

Session 5361cc7f encountered hook block when attempting to exit plan mode without displaying the plan first. The hook returned instructions to display the plan file and use AskUserQuestion with specific options.
```

---

#### 15. False Positive Verification Pattern

**Location:** `docs/learned/pr-operations/addressing-feedback.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Verification Before Code Changes

Always verify claimed issues by reading current code state before making changes.

### Pattern

1. **Receive claim**: Review comment says "function X doesn't exist"
2. **Grep first**: Search for function X in current codebase
3. **Verify state**: Determine if issue is real or already fixed
4. **Act appropriately**: Fix if needed, or resolve with explanation if already fixed

### Example

Session b6196a52 received claim about `generate_issue_branch_name` not existing. Agent:
1. Grepped source code to verify current state
2. Confirmed function was renamed to `generate_planned_pr_branch_name`
3. Updated documentation reference accordingly

**Anti-pattern:** Trusting documentation claims without verification leads to unnecessary or incorrect changes.
```

---

#### 16. PR Workflow Command Coordination

**Location:** `docs/learned/pr-operations/workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Preview-Address-Verify Workflow

The complete PR review response workflow demonstrated in sessions b6196a52 and b852e7e2:

### Phases

1. **Preview**: `/erk:pr-preview-address` to classify and preview actionable items
2. **Address**: `/erk:pr-address` with Task tool for proper classifier isolation
3. **Verify**: Re-run classifier via Task tool to confirm all threads resolved

### Key Requirements

- Use Task tool (not Skill invocation) for classifier
- Batch thread resolution via `erk exec resolve-review-threads`
- Single commit for all fixes when possible
- Verification phase confirms 0 remaining actionable threads

### Success Metrics

Session b6196a52:
- 2/2 threads resolved (100% success rate)
- 1 batch call instead of 2 individual calls (50% API reduction)
- 2 files modified in single commit
```

---

## Contradiction Resolutions

No contradictions found. The documentation is internally consistent following the comprehensive update in commit f556932fd (2026-02-25). The PR #8236 continues this synchronization work, maintaining consistency across 64 files.

## Stale Documentation Cleanup

No stale documentation found. The ExistingDocsChecker verified all code references and found zero phantom references. All documentation artifacts exist in the codebase.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. PlannedPRBackend Single-Arg Constructor

**What happened:** 7 separate PR review violations caught agents using outdated single-arg constructor pattern.
**Root cause:** Documentation examples lagged behind code changes during backend consolidation.
**Prevention:** Add tripwire warning and update all test examples to show 3-arg pattern.
**Recommendation:** TRIPWIRE (score 6 - highest priority)

### 2. Hook Blocking ExitPlanMode

**What happened:** PreToolUse:ExitPlanMode hook blocked because plan wasn't displayed to user first.
**Root cause:** Attempting to exit plan mode without following required preparation steps.
**Prevention:** Always read and display plan file before ExitPlanMode; use AskUserQuestion with structured options.
**Recommendation:** ADD_TO_DOC

### 3. Prettier Formatting Failure After Doc Edits

**What happened:** Markdown table column width changes violated prettier rules.
**Root cause:** Manual doc edits without running formatter.
**Prevention:** Run `prettier --write` immediately after manual table edits.
**Recommendation:** CONTEXT_ONLY (low severity, well-handled by devrun integration)

### 4. Trusting Documentation Claims Without Verification

**What happened:** Documentation claimed function X doesn't exist.
**Root cause:** Documentation can become stale when code is refactored.
**Prevention:** Always grep source code when fixing "X doesn't exist" claims to verify current state.
**Recommendation:** ADD_TO_DOC

### 5. erk exec update-pr-description Silent Failure

**What happened:** Command produced no output twice, failure not investigated.
**Root cause:** Unknown - no stderr captured, no investigation performed.
**Prevention:** Always check for non-empty output from erk exec commands returning JSON.
**Recommendation:** ADD_TO_DOC (new file for command error handling patterns)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. PlannedPRBackend Constructor Signature

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +1)
**Trigger:** Before creating PlannedPRBackend in tests
**Warning:** "Use 3-arg constructor: PlannedPRBackend(github, github_issues, time=FakeTime()), not single-arg PlannedPRBackend(fake_github)"
**Target doc:** `docs/learned/testing/tripwires.md`

This is the highest-priority tripwire because the same error pattern was caught 7 separate times during PR review. The constructor signature changed during backend consolidation, but outdated examples persist in documentation and agent training data. Without this tripwire, agents will continue to fail when writing tests that instantiate the backend.

### 2. context_for_test() Parameter Naming

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before using context_for_test()
**Warning:** "Parameter is plan_store (not plan_backend)"
**Target doc:** `docs/learned/testing/tripwires.md`

The naming mismatch between the backend class name (`PlannedPRBackend`) and the context factory parameter (`plan_store`) creates consistent confusion. Multiple PR review violations caught this same error pattern.

### 3. Test Helper Function Naming

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, Cross-cutting +1)
**Trigger:** Before creating plan store in tests
**Warning:** "Use create_plan_store_with_plans() for test setup, not create_plan_store()"
**Target doc:** `docs/learned/testing/tripwires.md`

Agents consistently guess the simpler function name. The `with_plans` suffix is meaningful but not intuitive.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Batch Thread Resolution

**Score:** 3/10 (Cross-cutting, External tool)
**Notes:** Used consistently across all three sessions but well-documented in command instructions. The pattern is clear once loaded. May warrant tripwire if agents continue to use individual calls despite instructions.

### 2. Task Tool for Subagent Isolation

**Score:** 3/10 (Non-obvious, Cross-cutting)
**Notes:** Specific to `--print` mode contexts. The distinction between Skill invocation and Task tool is subtle. Would benefit from a tripwire if the pattern extends beyond pr-feedback-classifier.

### 3. Outdated Thread Handling

**Score:** 2/10 (Non-obvious)
**Notes:** Specific to PR address workflow. The pattern is important but not cross-cutting enough to warrant a tripwire. Better suited as documentation in addressing-feedback.md.

### 4. Line Number References

**Score:** 2/10 (Cross-cutting)
**Notes:** General documentation best practice. While applicable to all docs, the harm is gradual (drift over time) rather than immediate failure. Better as strong guidance in source-pointers.md.

### 5. FakeGitHub API Naming

**Score:** 3/10 (Non-obvious, Repeated pattern)
**Notes:** The `updated_pr_bodies` vs `updated_prs` confusion was caught multiple times. Needs comprehensive reference documentation more than a tripwire - agents need to know the full API, not just avoid one mistake.
