# Documentation Plan: Fix erk one-shot dispatch metadata writing for draft_pr backend

## Context

This work extended erk's one-shot dispatch workflow to properly support the `draft_pr` backend, a significant architectural evolution that required understanding the fundamental difference in entity lifecycle between plan backends. In the github backend, the plan entity is a skeleton issue that exists before the PR; in the draft_pr backend, the plan entity IS the draft PR itself. This seemingly simple distinction cascaded into three distinct code changes across the dispatch flow, each requiring careful guards to prevent metadata corruption or self-referential entity operations.

The implementation journey revealed critical insights about test isolation in backend-conditional code. The initial "band-aid" fix (simply skipping an operation for draft_pr) masked a deeper architectural issue: the one-shot dispatch conflated "naming entity" and "plan entity" concepts. User intervention after the initial fix prompted a complete refactoring that properly models the entity lifecycle for both backends. This demonstrates the value of the "does this feel like a hack?" checkpoint.

Future agents working on plan backends will benefit from understanding: (1) how `plan_issue_number` can refer to either an issue or PR depending on backend, (2) why context-based backend detection (`ctx.plan_backend.get_provider_name()`) is superior to environment variable detection (`get_plan_backend()`), and (3) the three distinct application sites for backend-conditional logic in one-shot dispatch.

## Raw Materials

https://gist.github.com/schrockn/73dd986b896dd1203bc19efdef8e0775

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 16 |
| Contradictions to resolve | 1 |
| Tripwire candidates (score>=4) | 4 |
| Potential tripwires (score 2-3) | 3 |

## Documentation Items

### HIGH Priority

#### 1. Backend-conditional one-shot dispatch lifecycle

**Location:** `docs/learned/planning/one-shot-workflow.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7720]

**Draft Content:**

```markdown
## Backend-Conditional Dispatch Logic

The one-shot dispatch flow diverges based on plan backend at three distinct points:

### Entity Creation

The `dispatch_one_shot()` function detects the backend via `ctx.plan_backend.get_provider_name()`:

- **github backend**: Creates a skeleton issue first, uses issue number for `P<N>-` branch naming
- **draft_pr backend**: Skips skeleton issue entirely, uses `generate_draft_pr_branch_name()` for `plan/` prefix

See `src/erk/cli/commands/one_shot_dispatch.py` for the implementation.

### PR Creation

PR body construction differs by backend:

- **github backend**: Plain body referencing the skeleton issue
- **draft_pr backend**: Includes plan-header metadata block via `format_plan_header_body()`

### Post-Dispatch PR Body Update

After workflow dispatch:

- **github backend**: Updates PR body with workflow run link
- **draft_pr backend**: Skips update to preserve metadata block (critical: rewriting would corrupt plan state)

### Plan Entity Unification

After PR creation in draft_pr mode, `plan_issue_number = pr_number` is set. This allows all downstream code (workflow inputs, metadata writes, comments) to operate uniformly without additional backend checks.
```

---

#### 2. Self-referential close prevention tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7720]

**Draft Content:**

```markdown
## Self-Referential Close Prevention

**Trigger:** Before adding `Closes #N` to a draft PR body when the issue number equals the PR number

**Warning:** Draft PR IS the plan entity in draft_pr backend. Adding a self-referential close directive (`Closes #N` where N is the PR number) would cause the PR to close itself on merge, destroying the plan.

**Guard pattern:**
```python
if issue_number == pr_number:
    # Self-referential: skip closing ref
    return
```

**Score:** 9/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2, External tool quirk +1)

See `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` for the guard implementation.
```

---

#### 3. One-shot metadata block preservation tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7720]

**Draft Content:**

```markdown
## One-Shot Metadata Block Preservation

**Trigger:** Before rewriting draft PR body in one-shot dispatch after workflow trigger

**Warning:** Draft PR body contains a plan-header metadata block. Rewriting without extracting the metadata prefix corrupts plan backend state, causing metadata parsing failures and workflow dispatch issues.

**Guard pattern:**
For draft_pr backend, skip the post-dispatch PR body update entirely. The metadata block was written during PR creation and must be preserved.

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1, External tool quirk +1)

See `src/erk/cli/commands/one_shot_dispatch.py` for the conditional skip logic.
```

---

#### 4. Context-based backend detection tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] + [PR #7720]

**Draft Content:**

```markdown
## Context-Based Backend Detection

**Trigger:** Before using `get_plan_backend()` in code that has access to a context object

**Warning:** `get_plan_backend()` reads directly from `ERK_PLAN_BACKEND` environment variable. This bypasses test context injection, causing environment variable leakage from the developer's shell into tests. Tests will fail unpredictably based on the developer's environment.

**Pattern:**
```python
# WRONG: Environment variable leakage
backend = get_plan_backend()

# RIGHT: Respects injected test context
backend = ctx.plan_backend.get_provider_name()
```

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1)

This pattern is essential for any backend-conditional production code that also needs deterministic test coverage.
```

---

#### 5. Environment variable isolation in backend tests

**Location:** `docs/learned/testing/backend-testing.md` (CREATE)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for backend-conditional code
  - tests fail differently in CI vs local development
  - tests using env_overrides parameter
---

# Backend Testing Isolation

## The Problem

Tests using `env_overrides=None` inherit the developer's real environment variables. When code uses `get_plan_backend()` to read `ERK_PLAN_BACKEND`, tests become flaky based on the developer's shell configuration.

## Solution Patterns

### 1. Explicit Plan Store Injection

When testing draft_pr backend behavior, pass `plan_store` explicitly:

```python
plan_store = DraftPRPlanBackend(github, issues, time=FakeTime())
ctx = build_workspace_test_context(env, plan_store=plan_store)
```

This overrides the `context_for_test` heuristic that defaults to `GitHubPlanStore`.

### 2. Production Code: Context-Based Detection

Use `ctx.plan_backend.get_provider_name()` instead of `get_plan_backend()` so tests can inject the backend via context.

### 3. Explicit Environment Overrides

When testing github backend behavior specifically:

```python
env_overrides={"ERK_PLAN_BACKEND": "github"}
```

## Context Creation Chain

Understanding how test context is built:

1. `build_workspace_test_context(env, issues=issues)`
2. -> `env.build_context(issues=issues, **kwargs)`
3. -> `context_for_test(issues=issues)` in `erk/core/context.py`
4. -> Creates `GitHubPlanStore(issues)` when `plan_store` not explicit

The `issues` kwarg triggers a heuristic that creates GitHubPlanStore, bypassing any environment variable detection.
```

---

#### 6. One-shot backend support table update (contradiction resolution)

**Location:** `docs/learned/planning/plan-creation-pathways.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

```markdown
<!-- UPDATE this table row -->

| One-shot dispatch (`one_shot_dispatch`) | Backend-aware (github or draft_pr) | Skeleton issue (github only), Draft PR (draft_pr only) |
```

The existing documentation states one-shot only supports github backend with skeleton issues. This is now incorrect. One-shot dispatch supports both backends:
- **github backend**: Creates skeleton issue, uses `P<N>-` branch naming, writes metadata to issue
- **draft_pr backend**: Skips skeleton issue, uses `plan/` branch naming, writes metadata to draft PR

---

### MEDIUM Priority

#### 7. Backend naming conventions glossary

**Location:** `docs/learned/planning/backend-naming-conventions.md` (CREATE)
**Action:** CREATE
**Source:** [PR #7720]

**Draft Content:**

```markdown
---
read-when:
  - naming plan backends in code or comments
  - reviewers confused about backend terminology
  - choosing between "github" vs "github-issue" vs "draft_pr"
---

# Backend Naming Conventions

## Provider Names in Code

The canonical provider names returned by `get_provider_name()`:

| Backend | Provider Name | Branch Prefix |
|---------|---------------|---------------|
| GitHub Issue Backend | `"github"` | `P<N>-` |
| Draft PR Backend | `"github-draft-pr"` | `plan/` |

## Configuration Values

The `ERK_PLAN_BACKEND` environment variable accepts:

| Value | Backend |
|-------|---------|
| `github` | GitHub Issue Backend (default) |
| `draft_pr` | Draft PR Backend |

## Common Confusion

- **"github" vs "github-issue"**: Code uses `"github"` (short form), documentation sometimes says "github-issue" for clarity. Both refer to the same backend.
- **"draft_pr" vs "github-draft-pr"**: Config uses `draft_pr`, code returns `"github-draft-pr"` from `get_provider_name()`.
```

---

#### 8. Band-aid vs root cause detection

**Location:** `docs/learned/planning/band-aid-detection.md` (CREATE)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - fixing a bug feels like a hack
  - questioning whether a fix addresses root cause
  - user challenges implementation approach
---

# Band-Aid Detection Pattern

## The Checkpoint

After implementing a fix that makes tests pass, ask: **"Does this feel like a hack?"**

Signs of a band-aid fix:
- Adding a backend-conditional skip without understanding why the operation fails
- Guard clauses that check for specific backends to avoid errors
- Comments explaining "this is needed because..."

## The Session Pattern

This pattern was demonstrated in Session 876e540b:

1. Implemented the requested fix (skip operation for draft_pr)
2. Tests passed, PR submitted
3. **User questioned**: "this PR feels like a hack and might indicate we have not properly modelled lifecycle"
4. Agent agreed and identified root cause: entity conflation
5. Created follow-up plan for proper fix
6. Implemented proper solution in same session

## Key Learning

PR submission doesn't mean work is complete if the solution feels architecturally wrong. The user intervention revealed that the minimal fix masked a deeper issue: `dispatch_one_shot()` conflated "naming entity" and "plan entity" concepts.

## Prevention

When implementing fixes for backend-conditional behavior:
1. First implement the minimal fix
2. Ask: "Does this feel like a hack?"
3. If yes: Document the architectural issue and either fix properly or create follow-up
```

---

#### 9. Backend entity modeling divergence

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Entity Lifecycle Divergence

Add section documenting the fundamental difference in entity lifecycles:

### GitHub Backend

```
skeleton issue (plan entity) -> branch -> PR (implementation entity)
```

The skeleton issue IS the plan entity. It exists before any implementation begins.

### Draft PR Backend

```
branch -> draft PR (plan entity, unified)
```

The draft PR IS the plan entity. No skeleton issue is needed or created.

### Implications

This divergence affects:
1. **Branch naming**: github uses `P<N>-` (issue number), draft_pr uses `plan/` prefix
2. **Metadata target**: github writes to issue, draft_pr writes to PR
3. **Entity identity**: `plan_issue_number` may be issue number OR PR number

The "plan entity unification" pattern assigns `plan_issue_number = pr_number` after PR creation in draft_pr mode, allowing downstream code to treat both backends uniformly.
```

---

#### 10. Plan backend detection code pattern

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Backend Detection in Code

When writing backend-conditional logic, use the context-based pattern:

```python
is_draft_pr = ctx.plan_backend.get_provider_name() == "github-draft-pr"

if is_draft_pr:
    # draft_pr path
else:
    # github path
```

**Why not `get_plan_backend()`?**

The `get_plan_backend()` function reads directly from the `ERK_PLAN_BACKEND` environment variable. This creates test isolation problems: tests without explicit environment overrides inherit the developer's shell configuration.

Using `ctx.plan_backend.get_provider_name()` respects the injected test context, enabling deterministic test coverage.
```

---

#### 11. Test context injection with explicit plan_store

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Plan Store Injection

When testing non-default plan backends, pass `plan_store` explicitly:

```python
# Testing draft_pr backend
plan_store = DraftPRPlanBackend(github, issues, time=FakeTime())
ctx = build_workspace_test_context(env, plan_store=plan_store)
```

Do not rely on `ERK_PLAN_BACKEND` environment variable for test backend selection. The `context_for_test` function has heuristics that may override environment variables when certain parameters (like `issues`) are passed.
```

---

#### 12. Repository owner detection pattern

**Location:** `docs/learned/integrations/github-cli.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Repository Owner Detection

When using GitHub GraphQL API to query PR data, don't assume the repository owner from git config or working directory. Always verify first:

```bash
gh pr view <number> --json url
```

Extract the owner from the URL, then use in GraphQL queries. This prevents `NOT_FOUND` errors when working in forked repositories or worktrees with different remote configurations.
```

---

#### 13. Accepting best-effort operations in tests

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Best-Effort Operations in Tests

Some operations are wrapped in try/except with warning logs (like queued comment posting). These may fail in fakes due to gateway limitations:

- `FakeGitHubIssues.add_comment()` requires the issue to exist
- GitHub treats PRs as issues for commenting, but `FakeGitHub` separates them

**Testing approach:**
- Focus assertions on critical paths (e.g., dispatch metadata writes)
- Accept that best-effort operations may fail in fakes
- Document fake limitations where they cause test behavior to diverge from production
```

---

#### 14. plan_issue_number dual semantics

**Location:** `docs/learned/workflows/one-shot-workflow.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Workflow Input Semantics

The `plan_issue_number` workflow input has dual semantics:

| Backend | Meaning |
|---------|---------|
| github | Issue number of the skeleton plan issue |
| draft_pr | PR number of the draft PR (the plan entity) |

This is intentional: the "plan entity unification" pattern allows downstream workflow steps to reference the plan entity uniformly without backend-specific logic.

See `.github/workflows/one-shot.yml` for the input definition.
```

---

### LOW Priority

#### 15. Hardcoded test assertions against generated values

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Dynamic Test Assertions

**Trigger:** Before hardcoding PR/issue numbers in test assertions

**Warning:** FakeGitHub assigns PR numbers starting from 999, not 1. Hardcoded assertions like `assert pr_number == 1` will fail.

**Pattern:**
```python
# WRONG
result = dispatch_one_shot(...)
assert labels_applied_to_pr(1)

# RIGHT
result = dispatch_one_shot(...)
assert labels_applied_to_pr(result.pr_number)
```

Use dynamic values from function results in assertions.
```

---

#### 16. Test context heuristics override pattern

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Context Heuristics Override

The `context_for_test` function has heuristics that may override environment variables:

- Passing `issues=issues` kwarg triggers creation of `GitHubPlanStore` regardless of `ERK_PLAN_BACKEND`
- This prioritizes explicit parameters over environment detection

To test a specific backend, pass `plan_store` explicitly rather than relying on environment variable detection.
```

---

## Contradiction Resolutions

### 1. One-shot backend support

**Existing doc:** `docs/learned/planning/plan-creation-pathways.md` line 20
**Conflict:** States "One-shot dispatch (`one_shot_dispatch`) | Issue-based (GitHubPlanStore) | Skeleton issue" implying one-shot only supports github backend
**Resolution:** Update table row to reflect dual-backend support: "One-shot dispatch (`one_shot_dispatch`) | Backend-aware (github or draft_pr) | Skeleton issue (github only), Draft PR (draft_pr only)"

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Environment Variable Bleed into Tests

**What happened:** Tests using `env_overrides=None` failed when developer had `ERK_PLAN_BACKEND=draft_pr` set in their shell
**Root cause:** `get_plan_backend()` reads directly from `os.environ`, inheriting real environment when tests don't override
**Prevention:** Always use explicit env overrides when tests depend on specific env var values, or use context injection pattern
**Recommendation:** TRIPWIRE (added as Context-Based Backend Detection tripwire)

### 2. Band-Aid Fixes Papering Over Architecture

**What happened:** Initial fix simply skipped `write_dispatch_metadata()` for draft_pr backend
**Root cause:** Implementing minimal fix without questioning whether it addresses root cause vs symptoms
**Prevention:** After implementing a fix, ask "Does this feel like a hack?" If yes, document architectural issue and create follow-up
**Recommendation:** ADD_TO_DOC (added as Band-Aid Detection pattern)

### 3. Test Context Heuristics Overriding Backend

**What happened:** Tests passing `issues=issues` kwarg always got `GitHubPlanStore` regardless of environment variable
**Root cause:** `context_for_test` prioritizes explicit `issues` parameter over environment variable detection
**Prevention:** When testing non-default backends, pass `plan_store` explicitly
**Recommendation:** ADD_TO_DOC (added to testing docs)

### 4. Hardcoded Test Assertions

**What happened:** Test asserted PR #1, but FakeGitHub starts at 999
**Root cause:** Assumption about fake implementation details
**Prevention:** Always use dynamic values from function results in assertions
**Recommendation:** ADD_TO_DOC (added to testing tripwires)

### 5. Fake Gateway Limitations

**What happened:** Queued comment posting failed because FakeGitHubIssues doesn't recognize PRs as issues
**Root cause:** GitHub's API treats PRs as issues for commenting, but fake separates them
**Prevention:** Document fake limitations and adjust test expectations for best-effort operations
**Recommendation:** CONTEXT_ONLY

### 6. GitHub GraphQL Repository Owner Error

**What happened:** GraphQL query failed with NOT_FOUND because owner was assumed from working directory
**Root cause:** Hardcoded repository owner without verifying correct owner
**Prevention:** Before GraphQL queries on PRs, run `gh pr view` to extract correct owner/name from URL
**Recommendation:** ADD_TO_DOC (added to GitHub CLI docs)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Self-Referential Close Prevention

**Score:** 9/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +2, External tool quirk +1)
**Trigger:** Before adding `Closes #N` to draft PR body when issue_number == pr_number
**Warning:** Draft PR IS the plan entity in draft_pr backend. Self-referential close would close the plan itself on merge. Guard with: `if issue_number == pr_number: skip`
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the failure mode is catastrophic (plan destroyed on PR merge) and completely silent (GitHub closes the PR without any warning). The guard pattern is non-obvious: it only applies when issue and PR numbers are equal, which only happens in draft_pr mode.

### 2. One-Shot Metadata Block Preservation

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before rewriting draft PR body in one-shot dispatch after workflow trigger
**Warning:** Draft PR body contains plan-header metadata block. Rewriting without extracting metadata prefix corrupts plan backend state. Skip PR body update for draft_pr backend.
**Target doc:** `docs/learned/planning/tripwires.md`

This extends the existing draft-pr-lifecycle metadata preservation tripwire to the specific case of one-shot post-dispatch PR body updates.

### 3. Context-Based Backend Detection

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1)
**Trigger:** Before using `get_plan_backend()` in code that has access to context
**Warning:** Use `ctx.plan_backend.get_provider_name()` instead to respect injected test context and avoid environment variable brittleness
**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire is valuable because the failure mode (environment variable leakage) manifests as flaky tests that pass for some developers and fail for others, depending on their shell configuration.

### 4. Backend-Conditional Skeleton Issue Creation

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, Repeated pattern +1)
**Trigger:** Before creating skeleton issue in one-shot dispatch without checking plan backend
**Warning:** Only github backend uses skeleton issues for branch naming. draft_pr backend uses `plan/` prefix and creates the PR directly. Guard with: `if not is_draft_pr: create_skeleton_issue()`
**Target doc:** `docs/learned/planning/tripwires.md`

Creating unnecessary skeleton issues for draft_pr backend wastes GitHub resources and confuses the plan lifecycle.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Context Heuristics Override

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Only affects tests, not production code. Promotes if more developers hit this issue.

### 2. Hardcoded Test Assertions

**Score:** 2/10 (Repeated pattern +1, Silent failure +1)
**Notes:** Low severity, caught by test failures. Not silent enough to warrant tripwire.

### 3. Repository Owner Detection

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Only affects GraphQL queries, not standard `gh` CLI commands. Promotes if more APIs require correct owner.

---

## Cross-References to Existing Documentation

This PR builds on patterns documented in:

1. **Draft PR Lifecycle** (`docs/learned/planning/draft-pr-lifecycle.md`)
   - Lines 96-98: Self-referential close prevention (now applied to one-shot)
   - Lines 13-16: Metadata preservation tripwire (now applied to one-shot PR body updates)

2. **One-Shot Workflow** (`docs/learned/planning/one-shot-workflow.md`)
   - Lines 44-67: Skeleton plan issue pattern (now backend-conditional)
   - Lines 116-118: Branch naming patterns (now includes `plan/` prefix for draft_pr)
   - Lines 112-134: Dispatch metadata two-phase write (needs backend-specific extension)

3. **Plan Creation Pathways** (`docs/learned/planning/plan-creation-pathways.md`)
   - Line 20: One-shot dispatch backend support (NEEDS UPDATE - currently states issue-based only)

4. **Draft PR Plan Backend** (`docs/learned/planning/draft-pr-plan-backend.md`)
   - Architecture section (should add cross-reference to one-shot dispatch)

5. **Branch Naming** (`docs/learned/erk/branch-naming.md`)
   - Should be updated to document when one-shot uses `plan/` prefix vs `P<N>-` prefix
