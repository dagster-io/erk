# Documentation Plan: PR-Based Plan Review Workflow

## Context

This implementation adds a **PR-based plan review workflow** to Erk, enabling asynchronous review of plans before implementation begins. The implementation spans PR #6214 (Objective #6201 Steps 1.3 and 1.4) with 774 lines added across 8 files, three new exec commands, and comprehensive test coverage (12 new tests).

The core innovation is using draft PRs as a review surface for plan content. When a plan issue exists in GitHub, users can create a draft PR containing the plan file, enabling inline review comments on the plan itself. The `review_pr` metadata field tracks this relationship bidirectionally: the PR body references the plan issue, and the plan issue metadata stores the PR number. This pattern of "bidirectional linkage" is reusable for any artifact tracking scenario.

Documentation is critical because this workflow introduces several non-obvious patterns: multi-step operations where failure can leave orphaned artifacts, the distinction between review PRs (draft, never merged) and implementation PRs (merged after review), and the BodyContent type wrapper required by GitHub APIs. Without documentation, future agents will encounter the same type errors and test assertion failures that were resolved during this implementation.

## Raw Materials

Session and diff analysis files available at:
- Session: `.erk/scratch/sessions/74bec32a-0390-4674-9a86-61c6d5ab5e99/learn-agents/session-b086e1e3-fc5e-40b6-bb18-3fe53d8a7357.md`
- Diff: `.erk/scratch/sessions/74bec32a-0390-4674-9a86-61c6d5ab5e99/learn-agents/diff-analysis.md`

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 9 |
| New documents to create | 1 |
| Existing documents to update | 5 |
| Tripwire candidates (score >= 4) | 2 |
| Potential tripwires (score 2-3) | 2 |
| Contradictions to resolve | 0 |

---

## Documentation Items

### HIGH Priority

#### 1. PR-Based Plan Review Workflow Guide

**Location:** `docs/learned/planning/pr-review-workflow.md` (NEW)
**Action:** CREATE
**Sources:** [Session], [Diff]

This is the primary documentation artifact. The new workflow enables asynchronous plan review via draft PRs, and no existing documentation covers this pattern.

**Draft Content:**

```markdown
---
title: PR-Based Plan Review Workflow
read_when:
  - "creating a PR for plan review"
  - "setting up asynchronous plan review"
  - "understanding review_pr metadata field"
tripwires:
  - action: "creating a review PR for a plan"
    warning: "Review PRs are draft and never merged. They exist only for inline comments. Use plan-create-review-pr command."
---

# PR-Based Plan Review Workflow

Enable asynchronous plan review by creating draft PRs that contain plan content for inline commenting.

## Overview

The review workflow creates a draft PR containing the plan file, enabling reviewers to leave inline comments on specific parts of the plan before implementation begins.

**Key distinction:** Review PRs are NEVER merged. They exist solely as a commenting surface. Implementation PRs are separate and created later.

## Workflow Steps

### 1. Create Review Branch

```bash
erk exec plan-create-review-branch --issue <plan-issue-number>
```

Creates a branch containing the plan file extracted from the GitHub issue.

### 2. Create Review PR

```bash
erk exec plan-create-review-pr --issue <plan-issue-number>
```

Creates a draft PR targeting master with:
- Plan file as the diff content
- PR body linking back to plan issue
- Warning that this PR is for review only

### 3. Review and Comment

Reviewers add inline comments on the plan PR. Comments appear on specific lines of the plan content.

### 4. Address Feedback

Plan author updates the plan issue based on feedback, then optionally recreates the review PR.

## Bidirectional Linkage Pattern

The workflow maintains bidirectional references:

| Direction | Location | Content |
|-----------|----------|---------|
| PR -> Issue | PR body | `**Plan Issue:** #<issue_number>` |
| Issue -> PR | Metadata block | `review_pr: <pr_number>` |

This enables:
- Navigating from PR to source plan
- Programmatic discovery of review PR from plan issue
- Status tracking (has plan been reviewed?)

## Multi-Step Operation Pattern

The `plan-create-review-pr` command performs a multi-step operation:

1. **Validate** - Check plan issue exists (LBYL)
2. **Create PR** - Call GitHub API to create draft PR
3. **Capture ID** - Store returned PR number
4. **Update Metadata** - Add `review_pr` field to plan issue

**Failure mode:** If step 4 fails, PR exists but metadata is not updated (orphaned PR).

**Recovery:** Re-running the command should detect the existing PR via branch lookup and update metadata.

## Why Draft PRs?

- Visual indicator that this isn't ready for merge
- Prevents accidental merging (GitHub blocks merge of drafts by default)
- Signals "for review only" to reviewers
- Distinguishes from implementation PRs

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Overall plan state management
- [Metadata Field Workflow](metadata-field-workflow.md) - How review_pr field was added
- [PR Operations](../cli/pr-operations.md) - PR duplicate prevention patterns
```

---

#### 2. review_pr Metadata Field Documentation

**Location:** `docs/learned/planning/learn-plan-metadata-fields.md` (UPDATE)
**Action:** UPDATE - Add new section for `review_pr` field
**Sources:** [Diff], [Session]

The `review_pr` field is a new addition to the plan-header schema. Users need to understand its purpose, type, and lifecycle.

**Draft Content (add after `created_from_workflow_run_url` section):**

```markdown
### `review_pr`

Tracks the draft PR created for asynchronous plan review.

- **Type**: `int | None`
- **When populated**: By `plan-create-review-pr` command after PR creation
- **Format**: GitHub PR number (positive integer)

**Purpose:**

This field enables programmatic discovery of which draft PR contains the plan's review-ready version. It supports:

- TUI display of review status
- Automated workflows checking if plan has been reviewed
- Navigation from plan issue to review PR

**Important:** The review PR is distinct from any implementation PR. Review PRs are:
- Always created as drafts
- Never merged (for review only)
- Contain plan content, not implementation

**CLI Usage:**

The field is set automatically by:

```bash
erk exec plan-create-review-pr --issue <issue_number>
```

To read the field:

```bash
erk exec get-plan-metadata --issue <issue_number> --field review_pr
```
```

---

#### 3. Multi-Step Artifact Creation Pattern (Tripwire)

**Location:** `docs/learned/planning/pr-review-workflow.md` (part of item #1)
**Action:** CREATE (included in workflow doc)
**Sources:** [Session] (prevention insights), [Diff]

This pattern appears whenever creating an artifact (PR, issue, etc.) and then updating metadata with the artifact's ID. The non-obvious failure mode is worth highlighting.

**Draft Content (already included in item #1 under "Multi-Step Operation Pattern"):**

The pattern is:
1. Create artifact -> 2. Get ID -> 3. Update metadata -> 4. Handle failures

Failure between steps 2 and 3 leaves an orphaned artifact. The recovery strategy is idempotent re-execution: detect existing artifact via query, then update metadata.

---

### MEDIUM Priority

#### 4. Concrete Example for Metadata Field Addition Pattern

**Location:** `docs/learned/planning/metadata-field-workflow.md` (UPDATE)
**Action:** UPDATE - Add `review_pr` as concrete example
**Sources:** [Session] (patterns discovered), [Diff]

The existing documentation describes the pattern abstractly. Adding `review_pr` as a worked example improves clarity.

**Draft Content (add as new section "## Concrete Example: review_pr Field"):**

```markdown
## Concrete Example: review_pr Field

The `review_pr` field was added following this workflow. Here's how each step was implemented:

### 1. schemas.py - Define the Field

```python
# Add to PlanHeaderFieldName
PlanHeaderFieldName = Literal[
    # ... existing fields ...
    "review_pr",
]

# Add constant
REVIEW_PR: Literal["review_pr"] = "review_pr"

# Add validation in validate_plan_header_data()
if REVIEW_PR in data and data[REVIEW_PR] is not None:
    if not isinstance(data[REVIEW_PR], int) or data[REVIEW_PR] <= 0:
        raise ValueError("review_pr must be a positive integer or null")
```

### 2. plan_header.py - Update Functions

Two functions were added (not threading through create):

```python
def update_plan_header_review_pr(issue_body: str, review_pr: int) -> str:
    """Update the review_pr field in an existing plan header."""
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("No plan-header metadata block found")

    updated_data = dict(block.data)
    updated_data[REVIEW_PR] = review_pr
    PlanHeaderSchema().validate(updated_data)

    return replace_metadata_block_in_body(issue_body, "plan-header", updated_data)

def extract_plan_header_review_pr(issue_body: str) -> int | None:
    """Extract the review_pr field from a plan header."""
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None
    return block.data.get(REVIEW_PR)
```

### Why Not Thread Through create_plan_header_block()?

Unlike fields set at plan creation time, `review_pr` is populated AFTER the plan issue exists - when the review PR is created. This requires an update-in-place pattern rather than threading through creation functions.

### 3-5. Remaining Steps

For this field, steps 3-5 (plan_issues.py, plan_save_to_issue.py, test fixtures) were NOT needed because:
- Field is set after issue creation, not during
- No CLI option needed (set by exec command)
- Tests use direct header manipulation
```

---

#### 5. Update erk exec Commands Reference

**Location:** `docs/learned/cli/erk-exec-commands.md` (UPDATE)
**Action:** UPDATE - Add entries for new commands
**Sources:** [Diff]

The reference documentation needs updating to include the three new commands.

**Draft Content (add to "Plan Operations" section):**

```markdown
### Plan Review Operations

- `plan-create-review-branch` - Create branch with plan file for review
- `plan-create-review-pr` - Create draft PR and update plan metadata
- `plan-submit-for-review` - Orchestrate full review submission workflow

#### plan-create-review-pr

Creates a draft PR for asynchronous plan review:

1. Validates plan issue exists
2. Creates draft PR with plan file as content
3. Updates plan issue metadata with `review_pr` field

**Arguments:**

| Option | Required | Description |
|--------|----------|-------------|
| `--issue` | Yes | Plan issue number |

**Output (JSON):**

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

**Error codes:**

| Code | Description |
|------|-------------|
| `issue_not_found` | Plan issue does not exist |
| `metadata_update_failed` | PR created but metadata update failed |
```

---

#### 6. Review PR Creation Pattern for PR Operations

**Location:** `docs/learned/cli/pr-operations.md` (UPDATE)
**Action:** UPDATE - Add section on review PR variant
**Sources:** [Diff], [Session]

The existing PR operations doc covers duplicate prevention. Review PRs use a different pattern (LBYL on issue, not duplicate PR check).

**Draft Content (add as new section "## Review PR Creation Pattern"):**

```markdown
## Review PR Creation Pattern

Review PRs for plan content follow a different pattern than implementation PRs.

### Why No Duplicate PR Check?

For implementation PRs, we check `gh pr list --head <branch>` to prevent duplicates. For review PRs, we skip this because:

1. Branch is created fresh for review (no pre-existing PR)
2. Re-running should update metadata, not skip creation
3. Orphaned PRs are handled by metadata update, not prevention

### LBYL Pattern Instead

Review PR creation uses Look Before You Leap on the **issue**, not the PR:

```python
# Check issue exists BEFORE creating PR
if not github_issues.issue_exists(issue_number):
    raise CreateReviewPRException("issue_not_found", ...)

# Create PR (no duplicate check)
pr = github.create_pr(
    title=f"[Review] Plan #{issue_number}",
    body=format_pr_body(issue_number),
    draft=True,
)

# Update issue metadata with PR number
updated_body = update_plan_header_review_pr(issue_body, pr.number)
github_issues.update_issue_body(issue_number, BodyText(content=updated_body))
```

### Error Handling

Multi-step operations use typed error codes:

```python
class CreateReviewPRException(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(message)
```

Error codes enable precise handling in calling code:

| Code | Meaning | Recovery |
|------|---------|----------|
| `issue_not_found` | Plan issue doesn't exist | Create plan first |
| `metadata_update_failed` | PR exists but metadata not set | Re-run to retry |
```

---

### LOW Priority

#### 7. FakeGitHub Test Behavioral Quirks

**Location:** `docs/learned/testing/testing.md` (UPDATE)
**Action:** UPDATE - Add FakeGitHub section
**Sources:** [Session] (errors resolved)

The implementation encountered test failures because FakeGitHub returns hardcoded values. This is worth documenting to prevent recurring issues.

**Draft Content (add as new section "### FakeGitHub Behavioral Quirks"):**

```markdown
### FakeGitHub Behavioral Quirks

FakeGitHub simplifies some behaviors that differ from real GitHub:

#### Hardcoded PR Numbers

`FakeGitHub.create_pr()` returns PR number **999**, not sequential IDs:

```python
# FakeGitHub implementation
def create_pr(self, ...) -> PullRequestInfo:
    return PullRequestInfo(number=999, ...)  # Always 999
```

**Test implication:** Don't assert on sequential PR numbers:

```python
# WRONG - assumes sequential IDs
assert result.pr_number == 1

# CORRECT - match fake behavior
assert result.pr_number == 999
```

#### Mutation Tracking

Use read-only properties to verify operations:

```python
github = FakeGitHub()
# ... perform operations ...

# Check what PRs were created
assert len(github.created_prs) == 1
assert github.created_prs[0].title == "Expected Title"
```

**Available tracking properties:**
- `created_prs: list[PullRequestInfo]` - PRs created via `create_pr()`
- `updated_issues: list[tuple[int, str]]` - Issues updated via `update_issue_body()`
```

---

#### 8. Exec Command Registration Reminder

**Location:** `docs/learned/cli/erk-exec-commands.md` (UPDATE)
**Action:** UPDATE - Add reminder about reference regeneration
**Sources:** [Session] (prevention insights)

The implementation required regenerating exec reference docs. This step is often forgotten.

**Draft Content (add note at end of document):**

```markdown
## Adding New Exec Commands

When adding new exec commands:

1. Create script in `src/erk/cli/commands/exec/scripts/`
2. Import in `group.py` and call `exec_group.add_command()`
3. **Regenerate reference docs:** `erk-dev gen-exec-reference-docs`

The third step is often forgotten, causing the reference docs to become stale.
```

---

#### 9. GitHub API BodyContent Type

**Location:** `docs/learned/cli/pr-operations.md` (UPDATE) or tripwire
**Action:** UPDATE or TRIPWIRE
**Sources:** [Session] (errors resolved)

This type requirement caused a type error during implementation. The fix is non-obvious from the function signature.

**Draft Content (add to pr-operations.md or as inline note):**

```markdown
### GitHub API Type Requirements

When updating issue or PR bodies, use the `BodyContent` wrapper type:

```python
from erk_shared.gateway.github.types import BodyText, BodyContent

# WRONG - raw string causes type error
github_issues.update_issue_body(issue_number, updated_body)

# CORRECT - wrap in BodyText
github_issues.update_issue_body(issue_number, BodyText(content=updated_body))
```

**Why:** `BodyContent` is a discriminated union (`BodyText | BodyFile`) supporting both inline content and file references. The type system enforces explicit wrapping.
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Type Mismatch: str vs BodyContent

**What happened:** Agent passed raw string to `update_issue_body()`, causing type checker failure.

**Root cause:** Function signature requires `BodyContent` (union of `BodyText | BodyFile`), not `str`. This isn't immediately obvious from the function name.

**Prevention:** Document the type requirement. When calling any `update_*_body()` function, wrap content in `BodyText(content=str)`.

**Recommendation:** TRIPWIRE (score 4) - Non-obvious, external tool quirk, prevents type errors.

### 2. Test Assertion: Hardcoded Fake Values

**What happened:** Tests expected PR number 1, but FakeGitHub returned 999.

**Root cause:** FakeGitHub simplifies implementation by returning hardcoded values instead of maintaining state.

**Prevention:** Document fake behaviors in testing reference. Assert on tracked mutations rather than specific return values when possible.

**Recommendation:** ADD_TO_DOC - Low severity, test-only impact.

### 3. Outdated Reference Documentation

**What happened:** New exec command not appearing in reference docs after creation.

**Root cause:** Reference docs are auto-generated and require explicit regeneration.

**Prevention:** Add reminder to exec command creation workflow: always run `erk-dev gen-exec-reference-docs`.

**Recommendation:** ADD_TO_DOC - Process documentation, not tripwire.

### 4. Formatting Violations

**What happened:** CI failed on formatting for newly created Python file.

**Root cause:** New files aren't automatically formatted during creation.

**Prevention:** Run `make format` after creating new Python files, or rely on CI to catch and fix.

**Recommendation:** CONTEXT_ONLY - Standard CI workflow handles this.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Multi-Step Artifact Creation with Metadata Update

**Score:** 5/10 (Non-obvious: +2, Cross-cutting: +2, Silent failure potential: +1)

**Trigger:** Before creating an artifact (PR, issue) and updating metadata with its ID

**Warning:** Multi-step create-then-update operations can leave orphaned artifacts. If metadata update fails after artifact creation, the artifact exists but isn't tracked. Design for idempotent re-execution: detect existing artifact via query, then update metadata.

**Target doc:** `docs/learned/planning/pr-review-workflow.md`

This pattern applies beyond just review PRs. Any time you create an artifact and need to store its ID in metadata elsewhere, you face this failure mode. The warning helps agents design recovery strategies upfront.

### 2. GitHub API BodyContent Type Wrapper

**Score:** 4/10 (Non-obvious: +2, External tool quirk: +2)

**Trigger:** Before calling `update_issue_body()` or similar GitHub API methods

**Warning:** GitHub body update APIs require `BodyContent` wrapper type. Use `BodyText(content=str)` for inline content, not raw strings. Import from `erk_shared.gateway.github.types`.

**Target doc:** `docs/learned/cli/pr-operations.md`

The type error message doesn't clearly indicate the solution. This tripwire saves agents from debugging time.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. FakeGitHub Hardcoded PR Number (999)

**Score:** 2/10 (Repeated pattern: +1, External tool quirk: +1)

**Notes:** This affects test assertions only, not production code. The impact is limited to test-writing scenarios. Documenting in the testing reference is sufficient; a tripwire may be overkill since the test failure message is clear.

### 2. Schema Extension Checklist (4 steps)

**Score:** 3/10 (Cross-cutting: +2, Repeated pattern: +1)

**Notes:** Already documented in `metadata-field-workflow.md` with a comprehensive checklist. A tripwire would be redundant given the existing documentation. The concrete example being added (item #4) further reduces the need.

---

## Related Documentation References

Cross-links for implementing agent:

| Topic | Document | Relationship |
|-------|----------|--------------|
| Plan lifecycle states | `docs/learned/planning/lifecycle.md` | Review PR is optional step in lifecycle |
| Metadata block structure | `docs/learned/architecture/metadata-blocks.md` | How plan-header blocks are parsed |
| PR duplicate prevention | `docs/learned/cli/pr-operations.md` | Contrast with review PR pattern |
| Exec command patterns | `docs/learned/cli/exec-command-patterns.md` | JSON output pattern used |
| Testing patterns | `docs/learned/testing/testing.md` | FakeGitHub usage |
| Fake-driven testing | `fake-driven-testing` skill | Test architecture philosophy |

---

## Implementation Checklist

For the implementing agent:

- [ ] Create `docs/learned/planning/pr-review-workflow.md` (item #1)
- [ ] Update `docs/learned/planning/learn-plan-metadata-fields.md` (item #2)
- [ ] Update `docs/learned/planning/metadata-field-workflow.md` (item #4)
- [ ] Update `docs/learned/cli/erk-exec-commands.md` (items #5, #8)
- [ ] Update `docs/learned/cli/pr-operations.md` (items #6, #9)
- [ ] Update `docs/learned/testing/testing.md` (item #7)
- [ ] Verify cross-references between documents
- [ ] Run CI to validate markdown formatting