# Plan: Consolidated Documentation for Learn Plans

> **Consolidates:** #6212, #6210, #6204, #6198, #6195, #6191

## Source Plans

| # | Title | Items Merged | Status |
|---|-------|--------------|--------|
| 6212 | Create erk exec plan-create-review-branch Command | 2 tripwire candidates | Merge |
| 6210 | Create erk exec plan-create-review-branch Command | 5 doc items | Merge |
| 6204 | Learn Plan: Issue #6202 - plan-submit-for-review Command | 6 doc items | Merge |
| 6198 | Consolidate erk init capability commands | 1 doc item (conditional) | Defer - consolidation not merged |
| 6195 | Phase 8: Complete Git Gateway Refactoring | 9 doc items | Merge |
| 6191 | Phase 8: Cleanup - Config & Repo Decision | 2 doc items | Merge (overlaps with #6195) |

## What Changed Since Original Plans

- All 3 Phase 8 subgateways (RepoOps, AnalysisOps, ConfigOps) are fully implemented in code
- `plan-create-review-branch` command is implemented and merged (PR #6207)
- `plan-submit-for-review` command is implemented and merged (PR #6203)
- Issue #6196 (capability consolidation) is still OPEN - not merged to master
- Several documentation files claimed as "COMPLETE" in plans do not exist

## Investigation Findings

### Corrections to Original Plans

- **#6212**: Claimed "No NEW Documentation Needed" but exec-script-patterns.md and gateway-testing.md don't exist
- **#6210**: Same issue - claimed documentation complete but files missing
- **#6198**: Assessment based on unmerged code - DEFER this plan
- **#6195/#6191**: Significant overlap on gateway-inventory.md updates - CONSOLIDATE

### Overlap Analysis

| Topic | Plans | Consolidated Action |
|-------|-------|---------------------|
| Gateway import path tripwire | #6212, #6210 | Single tripwire entry |
| FakeGit subgateway property access | #6212, #6210 | Single tripwire entry |
| erk-exec-commands.md update | #6210, #6204 | One update adding both commands |
| Gateway inventory update | #6195, #6191 | One update adding all 3 subgateways |
| Exec script patterns | #6210, #6204 | One new file covering both commands |

## Remaining Gaps (Prioritized)

### HIGH Priority - Core Documentation

1. **Update `docs/learned/cli/erk-exec-commands.md`** - Add both new commands
2. **Update `docs/learned/architecture/gateway-inventory.md`** - Add 3 Phase 8 subgateways
3. **Update `.claude/skills/erk-exec/SKILL.md`** - Add plan-submit-for-review and plan-create-review-branch

### MEDIUM Priority - New Documentation

4. **Create `docs/learned/cli/exec-script-patterns.md`** - Template structure for exec scripts
5. **Create `docs/learned/planning/pr-review-workflow.md`** - PR-based plan review workflow
6. **Create `docs/learned/testing/fake-github-testing.md`** - FakeGitHubIssues pitfall (comments_with_urls)

### LOW Priority - Tripwires & Enhancements

7. **Update `docs/learned/tripwires-index.md`** - Add gateway import path tripwire
8. **Update `docs/learned/tripwires-index.md`** - Add FakeGit subgateway access tripwire
9. **Update `docs/learned/planning/lifecycle.md`** - Add optional Review phase

### DEFERRED (blocked on #6196 merge)

10. **Verify `docs/learned/architecture/capability-system.md`** - After capability consolidation merges

## Implementation Steps

### Step 1: Update erk-exec-commands.md
**File:** `docs/learned/cli/erk-exec-commands.md`

Add to Plan Operations section:

```markdown
### plan-submit-for-review

Fetch plan content from a GitHub issue for PR-based review workflow.

**Usage:** `erk exec plan-submit-for-review <issue_number>`

**Output (JSON):**
- `success`, `issue_number`, `title`, `plan_content`, `plan_comment_id`, `plan_comment_url`

**Error Codes:** `issue_not_found`, `missing_erk_plan_label`, `no_plan_content`

### plan-create-review-branch

Creates a git branch for offline plan review.

**Usage:** `erk exec plan-create-review-branch <issue_number>`

**Output (JSON):**
- `success`, `issue_number`, `branch`, `file_path`, `plan_title`

**Error Codes:** `issue_not_found`, `missing_erk_plan_label`, `no_plan_content`, `branch_already_exists`, `git_error`
```

**Source:** Investigation of #6204, #6210
**Verification:** Command appears in reference table

---

### Step 2: Update gateway-inventory.md
**File:** `docs/learned/architecture/gateway-inventory.md`

Add to "Sub-Gateways" section (after line ~372):

```markdown
### GitRepoOps (`git/repo_ops/`)

Repository location and metadata operations.

- **Key Methods:** `get_repository_root()`, `get_git_common_dir()`
- **Fake Features:** Configurable repository paths, in-memory state
- **Added:** Phase 8 (PR #6190)

### GitAnalysisOps (`git/analysis_ops/`)

Branch comparison and analysis operations.

- **Key Methods:** `count_commits_ahead()`, `get_merge_base()`, `get_diff_to_branch()`
- **Fake Features:** Configurable commit counts, merge bases, diff content
- **Added:** Phase 8 (PR #6190)

### GitConfigOps (`git/config_ops/`)

Git configuration management operations.

- **Key Methods:** `config_set()`, `get_git_user_name()`
- **Fake Features:** In-memory configuration state
- **Added:** Phase 8 (PR #6190)
```

Also add Phase 8 completion note at end of Sub-Gateways section:

```markdown
> **Phase 8 Complete:** Git ABC refactoring achieved 10 total subgateways. All subgateways follow the 5-layer implementation pattern (abc, real, fake, dry_run, printing). Git ABC now serves as a pure property facade.
```

**Source:** Investigation of #6195, #6191
**Verification:** Entries match code at `packages/erk-shared/src/erk_shared/gateway/git/`

---

### Step 3: Update SKILL.md
**File:** `.claude/skills/erk-exec/SKILL.md`

Add to Plan Operations section (around line 39-49):

```markdown
- `plan-submit-for-review` - Extract plan content from issue for PR review
- `plan-create-review-branch` - Create review branch with plan content
```

**Source:** Investigation of #6204, #6210
**Verification:** Commands listed in skill reference

---

### Step 4: Create exec-script-patterns.md
**File:** `docs/learned/cli/exec-script-patterns.md`

```markdown
---
title: Exec Script Patterns
category: cli
read_when: Creating new exec CLI commands
---

# Exec Script Patterns

## Template Structure

### 1. Result Dataclasses

```python
@dataclass(frozen=True)
class MyCommandSuccess:
    success: Literal[True]
    # Command-specific fields
    result_value: str

@dataclass(frozen=True)
class MyCommandError:
    success: Literal[False]
    error: str  # Machine-readable error code
    message: str  # Human-readable description
```

### 2. Click Command Entry Point

```python
@click.command(name="my-command")
@click.argument("arg_name", type=int)
@click.pass_context
def my_command(ctx: click.Context, arg_name: int) -> None:
    """Brief description."""
    git = require_git(ctx)
    github_issues = require_github_issues(ctx)

    result = _my_command_impl(git, github_issues, arg_name)

    click.echo(json.dumps(asdict(result)))
    if isinstance(result, MyCommandError):
        raise SystemExit(1)
```

### 3. Gateway Import Paths

**IMPORTANT:** Gateway ABCs use submodule paths.

```python
# Correct
from erk_shared.gateway.github.issues.abc import GitHubIssues

# Incorrect - will raise ImportError
from erk_shared.gateway.github.abc import GitHubIssues
```

### 4. Plan Metadata Extraction

Reuse existing functions:
```python
from erk.cli.commands.exec.scripts.plan_submit_for_review import (
    extract_plan_header_comment_id,
    extract_plan_from_comment,
)
```

## Error Code Convention

Use lowercase snake_case error codes that are:
- Machine-readable (for programmatic handling)
- Descriptive (e.g., `missing_erk_plan_label` not `invalid_input`)
- Actionable (users understand what went wrong)

## Reference Implementations

- `plan_submit_for_review.py` - Plan content extraction
- `plan_create_review_branch.py` - Branch creation with plan file
```

**Source:** Investigation of #6210, #6204
**Verification:** Patterns match existing exec scripts

---

### Step 5: Create pr-review-workflow.md
**File:** `docs/learned/planning/pr-review-workflow.md`

```markdown
---
title: PR-Based Plan Review Workflow
category: planning
read_when: Reviewing plans collaboratively before implementation
---

# PR-Based Plan Review Workflow

## Overview

Alternative to immediate implementation: submit plans as temporary PRs for collaborative review.

## When to Use

- Plan is complex and needs multiple stakeholders to review
- Significant architectural decision requires team input
- Want feedback on approach before implementation

## Workflow Steps

1. Create plan via plan mode or `/erk:objective-next-plan`
2. Save to GitHub with `/erk:plan-save`
3. Run: `erk exec plan-submit-for-review <issue-number>`
4. Create temporary PR with plan content using returned data
5. Review and discuss in PR UI
6. Incorporate feedback into plan
7. Delete temporary PR branch
8. Implement plan normally via `erk plan submit`

## Command Reference

| Command | Purpose |
|---------|---------|
| `erk exec plan-submit-for-review <issue>` | Extract plan content from issue |
| `erk exec plan-create-review-branch <issue>` | Create review branch with plan file |

## Difference from Direct Implementation

- **Direct:** `erk plan submit` creates branch, PR, implements automatically
- **Review:** `erk exec plan-submit-for-review` returns data for manual review PR creation
```

**Source:** Investigation of #6204
**Verification:** Commands exist and work as documented

---

### Step 6: Create fake-github-testing.md
**File:** `docs/learned/testing/fake-github-testing.md`

```markdown
---
title: FakeGitHubIssues Testing Patterns
category: testing
read_when: Writing tests that use FakeGitHubIssues
---

# FakeGitHubIssues Testing Patterns

## Parameter Confusion: comments vs comments_with_urls

FakeGitHubIssues has two comment-related parameters:
- `comments: dict[int, list[str]]` - Simple comment bodies as strings
- `comments_with_urls: dict[int, list[IssueComment]]` - Full comment objects

### The Pitfall

If you pass string comments to the wrong parameter, tests fail with "no comments found".

```python
# WRONG - passes simple strings to comments_with_urls
fake_gh = FakeGitHubIssues(
    issues={123: issue},
    comments_with_urls={123: ["comment body"]},  # strings won't work!
)

# CORRECT - creates full IssueComment objects
comments = [IssueComment(id=1, url="...", body="...", author="...")]
fake_gh = FakeGitHubIssues(
    issues={123: issue},
    comments_with_urls={123: comments},
)
```

### Prevention

When setting up FakeGitHubIssues for testing:
1. Check which getter method you're calling in your code
2. Use matching parameter name (`comments` for `get_comments`, `comments_with_urls` for `get_issue_comments_with_urls`)
3. Ensure correct types for the parameter

## Reference Test File

See: `tests/unit/fakes/test_fake_github_issues.py` (1023 lines of comprehensive examples)
```

**Source:** Investigation of #6204
**Verification:** Pattern matches test file usage

---

### Step 7: Update tripwires-index.md
**File:** `docs/learned/tripwires-index.md`

Add to CLI/Testing section:

```markdown
### Exec Script Patterns

**Before importing from `erk_shared.gateway` when creating exec commands:**
- Read: [Exec Script Patterns](cli/exec-script-patterns.md)
- Warning: Gateway ABCs use submodule paths: `erk_shared.gateway.{service}.{resource}.abc`

### FakeGit Subgateway Property Access

**Before accessing FakeGit properties in tests:**
- Read: [Testing Patterns](testing/testing.md#fakegit-property-access)
- Warning: Access properties via subgateway (e.g., `git.commit_ops.staged_files`), not top-level
```

**Source:** Investigation of #6212, #6210
**Verification:** Tripwires link to documentation files

---

### Step 8: Update lifecycle.md
**File:** `docs/learned/planning/lifecycle.md`

Add after Phase 2 (Plan Submission):

```markdown
### Phase 2b: Review (Optional)

For plans requiring collaborative review or validation:

1. Create temporary PR with plan content using `erk exec plan-submit-for-review`
2. Review and discuss in PR UI
3. Incorporate feedback
4. Delete review PR branch
5. Continue to Phase 3: Submit for Implementation

See [PR-Based Plan Review Workflow](pr-review-workflow.md) for details.
```

**Source:** Investigation of #6204
**Verification:** Links to new pr-review-workflow.md

---

## Attribution

Items by source:

- **#6212**: Steps 7 (tripwires)
- **#6210**: Steps 1, 4, 7
- **#6204**: Steps 1, 3, 5, 6, 8
- **#6198**: DEFERRED (blocked on #6196 merge)
- **#6195**: Steps 2
- **#6191**: Steps 2 (overlaps with #6195)

## Verification

1. **After Step 1:** `grep -c "plan-submit-for-review\|plan-create-review-branch" docs/learned/cli/erk-exec-commands.md` returns 2+
2. **After Step 2:** `grep -c "RepoOps\|AnalysisOps\|ConfigOps" docs/learned/architecture/gateway-inventory.md` returns 3+
3. **After Step 3:** `grep -c "plan-submit-for-review" .claude/skills/erk-exec/SKILL.md` returns 1+
4. **After Steps 4-6:** New files exist and are non-empty
5. **After Step 7:** `grep -c "exec-script-patterns\|FakeGit.*Subgateway" docs/learned/tripwires-index.md` returns 2+
6. **After Step 8:** `grep -c "Phase 2b\|Review (Optional)" docs/learned/planning/lifecycle.md` returns 1+
7. **Final:** Run `/local:all-ci` to ensure no regressions