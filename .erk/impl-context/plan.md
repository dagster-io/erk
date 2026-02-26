# Documentation Plan: Add retrack_branch to BranchManager ABC

## Context

This plan captures documentation insights from implementing `retrack_branch()` across the BranchManager ABC hierarchy. The implementation extended erk's dual-mode Git/Graphite abstraction by adding a new mutation method that already existed on the GraphiteBranchOps sub-gateway but was being called directly, bypassing the abstraction layer.

The implementation is a textbook example of the gateway ABC pattern in erk: adding an abstract method that Graphite implements via delegation to a sub-gateway while Git implements as a no-op (since Git doesn't track parent-child branch relationships). A future agent implementing similar gateway methods would benefit from understanding this 4-file pattern variance, and the call site simplification demonstrates the concrete value of proper abstraction layers.

The sessions showed excellent documentation-first discipline: the agent loaded the gateway ABC implementation checklist before starting, which prevented all common implementation pitfalls. This validates that the existing documentation infrastructure works well when agents use it properly.

## Raw Materials

PR #8242

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 10 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 0 |
| Potential tripwires (score 2-3) | 1 |

## Documentation Items

### HIGH Priority

#### 1. Update BranchManager abstraction documentation with retrack_branch method

**Location:** `docs/learned/architecture/branch-manager-abstraction.md`
**Action:** UPDATE
**Source:** [PR #8242]

**Draft Content:**

```markdown
## Additions to Existing Document

### Update Mutation Boundary Table

Add row for `retrack_branch`:

| Method | GraphiteBranchManager | GitBranchManager |
|--------|----------------------|------------------|
| retrack_branch | Delegates to GraphiteBranchOps, runs `gt track <branch> --no-interactive` | Silent no-op (Git doesn't track branch relationships) |

### Update Sub-Gateway Operations List

In the "Sub-Gateway Architecture" section, add `retrack_branch` to the list of GraphiteBranchOps operations exposed through BranchManager.

### Source Files

See `packages/erk-shared/src/erk_shared/gateway/branch_manager/` directory for implementation details.
```

#### 2. Update Git-Graphite quirks auto-fix pattern example

**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** [PR #8242]

**Draft Content:**

```markdown
## Update to "Graphite SHA Tracking Divergence" Section

### Auto-Fix Pattern (Updated)

The auto-fix for SHA tracking divergence now uses the BranchManager abstraction:

```python
# Proper pattern (uses abstraction)
if ctx.graphite.is_branch_diverged_from_tracking(ctx.git, repo_root, branch_name):
    ctx.branch_manager.retrack_branch(repo_root, branch_name)
```

This replaces the previous pattern that called the sub-gateway directly. The BranchManager abstraction handles mode detection internally.

### Where This Pattern Is Used

See `src/erk/cli/commands/pr/checkout_cmd.py` for the canonical example of divergence detection and auto-fix.
```

#### 3. Document BranchManager 4-file pattern variance

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Add New Section: "Pattern Variances by Gateway Type"

### BranchManager: 4-File Pattern

Unlike standard gateways that use the 5-file pattern (abc.py, real.py, fake.py, dry_run.py, printing.py), BranchManager uses a 4-file pattern:

- `abc.py` - Abstract base class defining the interface
- `git.py` - Plain Git implementation (many operations are no-ops)
- `graphite.py` - Graphite implementation (delegates to sub-gateways)
- `fake.py` - Test double implementation

**Why no dry_run.py or printing.py?**

BranchManager is a composition abstraction over lower-level gateways (GitBranchOps, GraphiteBranchOps) that already have dry_run and printing variants. BranchManager delegates to these sub-gateways, so the dry_run/printing behavior is inherited.

**When implementing new BranchManager methods:**

1. Add abstract method to `abc.py`
2. Add implementation (often no-op) to `git.py`
3. Add delegating implementation to `graphite.py`
4. Add tracking implementation to `fake.py`

No need to create dry_run.py or printing.py implementations.

### Source Files

See `packages/erk-shared/src/erk_shared/gateway/branch_manager/` directory for the implementation.
```

---

### MEDIUM Priority

#### 4. Add frozen dataclass test double mutation tracking example

**Location:** `docs/learned/testing/frozen-dataclass-test-doubles.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Add Example: FakeBranchManager Mutation Tracking

### Pattern: List Tracking with Property Accessor

When a fake implementation needs to track method calls while maintaining the frozen dataclass constraint:

1. **Private mutable field**: `_retracked_branches: list[str] = field(default_factory=list)`
2. **Mutation method**: Appends to the tracking list
3. **Public property**: Returns copy for assertions

This pattern allows tests to verify mutation calls without breaking the frozen dataclass invariant.

### Test Assertion Pattern

```python
# Test verifies that retrack_branch was called with correct argument
assert fake_branch_manager.retracked_branches == ["my-branch"]
```

### Source Files

See `packages/erk-shared/src/erk_shared/gateway/branch_manager/fake.py` for the FakeBranchManager implementation of this pattern.
```

#### 5. Document JSON context passing pattern

**Location:** `docs/learned/architecture/json-context-passing.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - designing exec scripts that return data to Claude agents
  - passing rich context between commands and AI
  - implementing multi-step command orchestration
tripwires: []
---

# JSON Context Passing Pattern

## Purpose

Exec scripts return structured JSON to Claude agents, enabling rich context passing without multiple subprocess invocations.

## Pattern Overview

Instead of Claude making multiple calls to gather information, a single exec script collects all relevant context and returns it as JSON. The Claude agent parses this JSON and uses the data natively.

## Benefits

1. **Efficiency**: Single subprocess call instead of many
2. **Structured data**: Type-safe parsing vs ad-hoc text extraction
3. **Complete context**: All related data gathered together
4. **AI-friendly**: Claude excels at JSON parsing and reasoning

## Example Usage

The `erk exec get-pr-context` command returns:

- Branch relationships (current, parent)
- PR metadata (number, URL)
- Diff file path (written to scratch storage)
- Commit messages array
- Optional plan context with objective summary

## When to Use

Use JSON context passing when:
- Multiple pieces of related data are needed
- Data comes from different sources (Git, GitHub, local files)
- AI needs structured data for reasoning
- Avoiding nested Claude subprocess calls

## Source Files

See `src/erk/exec/` directory for examples of exec scripts returning JSON context.
```

#### 6. Document PR submission workflow orchestration

**Location:** `docs/learned/pr-operations/pr-submission-workflow.md`
**Action:** CREATE (if doesn't exist) or UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - working on PR submission workflow
  - understanding how /erk:pr-submit works
  - designing multi-step Claude command workflows
tripwires: []
---

# PR Submission Workflow Architecture

## Overview

The `/erk:pr-submit` command uses a 5-step orchestrated flow designed to avoid nested Claude subprocess calls while keeping AI in the driver's seat.

## Workflow Steps

1. **Push + Create PR**: `erk exec push-and-create-pr` (mechanical, no AI)
2. **Gather Context**: `erk exec get-pr-context` returns JSON with diff, commits, plan context
3. **Generate Description**: Claude generates title + body natively (no subprocess)
4. **Apply Description**: `erk exec set-pr-description --body-file <path>` (mechanical)
5. **Validate**: `erk pr check --stage=impl` confirms invariants

## Key Design Principle

The Claude agent running `/erk:pr-submit` generates the PR description natively rather than spawning a subprocess. Mechanical operations are delegated to exec scripts.

## Validation Invariants

After submission, `erk pr check --stage=impl` validates:
- `.erk/impl-context/` is cleaned up
- Plan reference exists in PR body
- Checkout footer is present

## Source Files

See the pr-submit command in `.claude/commands/` for the orchestration logic.
```

#### 7. Document abstraction layer benefits with concrete example

**Location:** `docs/learned/architecture/branch-manager-abstraction.md`
**Action:** UPDATE (add teaching section)
**Source:** [Impl]

**Draft Content:**

```markdown
## Add Section: "Abstraction Value Demonstration"

### Call Site Simplification Example

The `retrack_branch` addition demonstrates how proper abstraction eliminates conditional logic at call sites.

**Before (leaked implementation detail):**

```python
if ctx.graphite_branch_ops is not None:
    ctx.graphite_branch_ops.retrack_branch(worktree_path, branch_name)
```

Callers had to:
1. Check if Graphite operations are available
2. Call the sub-gateway directly
3. Understand implementation details

**After (proper abstraction):**

```python
ctx.branch_manager.retrack_branch(worktree_path, branch_name)
```

Callers simply call the abstraction. Mode detection happens internally:
- Graphite mode: Delegates to GraphiteBranchOps
- Git mode: Silent no-op (appropriate behavior)

### Lesson

When you find code checking `ctx.<gateway> is not None` before calling methods, that's often a sign the method should be added to the abstraction layer.

### Source Files

See `src/erk/cli/commands/pr/checkout_cmd.py` for the call site that was simplified.
```

---

### LOW Priority

#### 8. Verify PR checkout documentation exists and is current

**Location:** Search for docs about `erk pr checkout` command
**Action:** UPDATE (if exists)
**Source:** [PR #8242]

**Draft Content:**

```markdown
## Conditional Update (if docs exist)

If PR checkout documentation exists, add note about automatic retracking:

### Divergence Auto-Fix

When checking out a PR branch, if Graphite tracking has diverged from the actual git SHA, the checkout command automatically retracks the branch. This uses the BranchManager abstraction to ensure correct behavior in both Graphite and Git modes.

Detection: `ctx.graphite.is_branch_diverged_from_tracking()`
Fix: `ctx.branch_manager.retrack_branch()`
```

#### 9. Update tripwire to explicitly include retrack_branch

**Location:** `docs/learned/architecture/branch-manager-abstraction.md` (tripwires section)
**Action:** UPDATE
**Source:** [PR #8242]

**Draft Content:**

```markdown
## Update Tripwire Action Pattern

The existing tripwire warning about direct sub-gateway calls should explicitly include `retrack_branch`:

**Current action pattern:**
"calling ctx.graphite_branch_ops mutation methods directly (track_branch, delete_branch, submit_branch)"

**Updated action pattern:**
"calling ctx.graphite_branch_ops mutation methods directly (track_branch, retrack_branch, delete_branch, submit_branch)"

This ensures agents are warned when attempting to bypass the BranchManager abstraction for any mutation operation.
```

#### 10. Validate impl-validation-checklist documentation

**Location:** `docs/learned/planning/impl-validation-checklist.md`
**Action:** UPDATE (verify exists and is current)
**Source:** [Impl]

**Draft Content:**

```markdown
## Validation Check

Verify that the document includes the following invariants checked by `erk pr check --stage=impl`:

1. `.erk/impl-context/` directory is not present (cleaned up after submission)
2. Plan reference found in PR body (trackability)
3. Checkout footer present in PR body (usability)

If not documented, add these as a checklist section showing what automated validation confirms.
```

## Contradiction Resolutions

No contradictions detected. The existing documentation fully supports the implemented changes. The existing tripwire in `branch-manager-abstraction.md` explicitly warns against calling `ctx.graphite_branch_ops` mutation methods directly, which aligns perfectly with this PR's goal.

## Stale Documentation Cleanup

No stale documentation detected. All code artifacts referenced in existing documentation were verified to exist and remain current.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Format Check Failure After Manual Edits

**What happened:** Manual edit of checkout_cmd.py broke line length formatting rules.
**Root cause:** Hand-edited code didn't respect ruff's line length limits.
**Prevention:** Run `ruff format <file>` immediately after any Edit tool usage that touches line breaks.
**Recommendation:** CONTEXT_ONLY (low severity, auto-fixable)

### 2. Stale Exec Reference Documentation

**What happened:** `.claude/skills/erk-exec/reference.md` was out of date with current exec commands.
**Root cause:** Auto-generated documentation not regenerated after prior changes.
**Prevention:** Include `erk-dev gen-exec-reference-docs` in CI pre-commit or fast-ci pipeline.
**Recommendation:** CONTEXT_ONLY (low severity, pre-existing issue)

## Tripwire Candidates

No items meet the tripwire-worthiness threshold (score >= 4). The BranchManager abstraction violation is already covered by an existing tripwire in `branch-manager-abstraction.md`. The only action needed is updating that tripwire to explicitly list `retrack_branch` in the method names.

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. BranchManager 4-file pattern awareness

**Score:** 3/10 (criteria: Non-obvious +2, Cross-cutting +1)
**Notes:** Developers familiar with the standard 5-file gateway pattern might waste time looking for dry_run.py/printing.py files that don't exist for BranchManager. However, this doesn't meet the threshold because:
- It's localized to BranchManager, not all gateways
- The consequence is confusion, not destructive behavior
- The gateway-abc-implementation.md update will document this explicitly

If future sessions show developers being confused by this pattern variance, consider promoting to a full tripwire.

## Implementation Notes

### Session Quality Observations

**Planning session (70a66fc1):**
- Excellent skill loading discipline (loaded pr-operations before starting)
- Proper complexity classification (cross_cutting triggered plan mode)
- Clean execution, no errors

**Implementation session (71443e74):**
- Documentation-first discovery (read gateway-abc-implementation.md upfront)
- Read all 4 files before making changes (efficient)
- Proper devrun delegation for CI operations
- Clean execution, only formatting issues (auto-fixed)
- 0 user corrections needed

**PR submission session (71443e74-part2):**
- Demonstrated mature workflow with 0 errors
- Heavy cache reuse (efficient token usage)
- Automated validation caught all invariants

### Key Takeaways

1. **Pre-loading documentation prevents errors**: Agent loaded gateway ABC implementation checklist before starting, avoiding all common pitfalls

2. **4-file vs 5-file pattern needs documentation**: Agent correctly identified BranchManager's variance, but this should be documented to help future developers

3. **Abstraction value demonstration**: The call site simplification is a concrete teaching example worth documenting

4. **No contradictions with existing docs**: The existing tripwire about direct sub-gateway calls perfectly anticipated this scenario

## Skipped Items

| Item | Reason |
|------|--------|
| `_retracked_branches` private field | Implementation detail tied to single test artifact (fake.py) |
| `retracked_branches` property (as standalone doc) | Single-artifact API, documented via example in test pattern doc |
| .claude/skills/erk-exec/reference.md update | Auto-generated file |
| PR address workflow execution | Already documented in pr-operations skill |
| Haiku subagent usage for classification | Already documented in planning/subagent-patterns.md |
| Branch slug generation rules | Internal planning convention, documented in pr-operations skill |
| Plan mode integration (ExitPlanMode hook) | Already documented in erk-planning skill |

## Summary of Actions

**Immediate (HIGH priority):**
1. Update branch-manager-abstraction.md with retrack_branch method details
2. Update git-graphite-quirks.md auto-fix pattern code example
3. Document BranchManager 4-file pattern variance in gateway-abc-implementation.md

**Follow-up (MEDIUM priority):**
4. Add frozen dataclass mutation tracking example to test doubles doc
5. Create new doc for JSON context passing pattern
6. Document PR submission workflow orchestration
7. Add abstraction benefits teaching example

**Verification (LOW priority):**
8. Check if PR checkout command docs exist and update if needed
9. Verify tripwire explicitly lists retrack_branch
10. Validate impl-validation-checklist.md exists and is current

**Total new docs to create:** 2 (json-context-passing.md, pr-submission-workflow.md)
**Total existing docs to update:** 6-8 (depending on verification results)
**Total items skipped:** 7
