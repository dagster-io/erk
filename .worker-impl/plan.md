# Documentation Plan: Create erk exec plan-create-review-branch Command

## Context

This implementation adds a new `erk exec plan-create-review-branch` command that creates isolated git branches for reviewing plan issues offline. The command fetches plan content from a GitHub issue (validating it has the `erk-plan` label and proper metadata), creates a `plan-review/<issue>` branch from `origin/master`, writes the plan content to a markdown file at the repo root, and pushes the branch to origin with upstream tracking.

The implementation followed established erk patterns: gateway abstraction for testability (Git and GitHubIssues ABCs), frozen dataclasses for structured JSON responses, comprehensive error codes for machine-readable failure handling, and fake-driven testing with 9 test cases covering success paths and all error conditions. Several valuable learnings emerged during implementation, particularly around gateway import paths (submodule organization) and FakeGit property access patterns (subgateway delegation).

Future agents would benefit from understanding: (1) the exec script template pattern that this command exemplifies, (2) the subgateway property access pattern in FakeGit that caused test debugging delays, and (3) the reusable plan metadata extraction functions that this command shares with `plan_submit_for_review`. Documenting these patterns prevents reimplementation and debugging friction for future plan-related exec scripts.

## Raw Materials

https://gist.github.com/schrockn/c158f64914db889566438dc2d7b80213

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 5 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 0 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. plan-create-review-branch command

**Location:** `/home/runner/work/erk/erk/docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [Impl], [PR #6207]

**Draft Content:**

```markdown
## Plan Operations (addition to existing section)

### plan-create-review-branch

Creates a git branch for offline plan review.

**Usage:** `erk exec plan-create-review-branch <issue-number>`

**Purpose:** Creates a `plan-review/<issue>` branch populated with plan content from a GitHub issue, enabling offline review without switching worktrees or affecting active work.

**Prerequisites:**
- Issue must have `erk-plan` label
- Issue must have plan-body metadata in a comment

**Output (JSON):**

Success:
```json
{
  "success": true,
  "issue_number": 1234,
  "branch": "plan-review/1234",
  "file_path": "PLAN-REVIEW-1234.md",
  "plan_title": "Plan Title Here"
}
```

Error:
```json
{
  "success": false,
  "error": "error_code",
  "message": "Human-readable description"
}
```

**Error Codes:**

| Code | Meaning | Recovery |
|------|---------|----------|
| `issue_not_found` | Issue doesn't exist | Verify issue number |
| `missing_erk_plan_label` | Issue lacks `erk-plan` label | Run `gh issue edit <number> --add-label erk-plan` |
| `no_plan_content` | Missing plan comment metadata | Ensure plan was saved via `/erk:plan-save` |
| `branch_already_exists` | Branch exists locally or on origin | Delete existing branch or use different workflow |
| `git_error` | Git operation failed | Check git status and network connectivity |

**Workflow Context:** Part of plan review workflow. Creates isolated branch for non-destructive plan examination before implementation.

**Note:** Plan file is written to repo root as `PLAN-REVIEW-<issue>.md`, not in `.impl/` or `docs/`.
```

---

#### 2. Branch naming safety (plan-review prefix)

**Location:** `/home/runner/work/erk/erk/docs/learned/git/branch-creation.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Branch Naming from Dynamic Data (addition to existing doc)

When creating branches from dynamic user input (e.g., issue numbers, plan titles), use prefixes to namespace them:

**Pattern:** `<prefix>/<dynamic-value>`

**Example:** `plan-review/1234` from issue #1234

**Why this matters:**
- Avoids collisions with user-created branches
- Groups related branches for easy identification (`git branch --list 'plan-review/*'`)
- Makes cleanup straightforward (`git branch -D plan-review/*`)

**Implemented in:**
- `plan-create-review-branch` uses `plan-review/<issue>` prefix
```

---

#### 3. Subgateway property access in tests

**Location:** `/home/runner/work/erk/erk/docs/learned/testing/gateway-testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## FakeGit Property Access (addition to existing doc)

### Subgateway Delegation Pattern

FakeGit delegates to subgateways, mirroring the real implementation structure. Properties must be accessed through their subgateway, not at the top level.

**Correct:**
```python
# Access staged_files through commit_ops subgateway
assert "myfile.md" in git.commit_ops.staged_files
```

**Incorrect:**
```python
# This will fail silently (empty list or AttributeError)
assert "myfile.md" in git.staged_files  # Wrong!
```

**Why this matters:**
- FakeGit mirrors real Git gateway architecture
- Accessing at wrong level gives empty results, causing confusing test failures
- Silent failure (empty list) is worse than AttributeError

**How to find the right path:**
1. Look at the method being called in implementation code
2. Find which subgateway (branch_ops, commit_ops, remote_ops) owns that method
3. Access the property via that same subgateway in tests

**Subgateway mapping:**
- `commit_ops` - staging, commits, `staged_files`
- `branch_ops` - branch creation, listing, current branch
- `remote_ops` - fetch, push, remote operations
```

---

### MEDIUM Priority

#### 1. Exec script template pattern

**Location:** `/home/runner/work/erk/erk/docs/learned/cli/exec-script-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# Exec Script Patterns

## Template Structure

Exec scripts follow a consistent template:

### 1. Result Dataclasses

Define frozen dataclasses for success and error responses:

```python
@dataclass(frozen=True)
class MyCommandSuccess:
    success: Literal[True]
    # Command-specific success fields
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
    """Brief description of command."""
    # Inject dependencies
    git = require_git(ctx)
    github_issues = require_github_issues(ctx)

    # Call implementation
    result = _my_command_impl(git, github_issues, arg_name)

    # Output JSON result
    click.echo(json.dumps(asdict(result)))

    # Exit with error code if failed
    if isinstance(result, MyCommandError):
        raise SystemExit(1)
```

### 3. Implementation Function

```python
def _my_command_impl(
    git: Git,
    github_issues: GitHubIssues,
    arg_name: int,
) -> MyCommandSuccess | MyCommandError:
    """Implementation with comprehensive docstring."""
    # Validate inputs
    # Execute work
    # Return structured result
```

### 4. Error Code Convention

Use lowercase snake_case error codes that are:
- Machine-readable (for programmatic handling)
- Descriptive (e.g., `missing_erk_plan_label` not `invalid_input`)
- Actionable (users can understand what went wrong)

### 5. Gateway Injection

Use Click context helpers:
- `require_git(ctx)` - Git operations
- `require_github_issues(ctx)` - GitHub issue operations
- `require_repo_root(ctx)` - Repository root path

## Examples

- `plan_create_review_branch.py` - Plan review branch creation
- `plan_submit_for_review.py` - Plan submission workflow
- `detect_trunk_branch.py` - Trunk branch detection
```

---

#### 2. Plan metadata extraction functions

**Location:** `/home/runner/work/erk/erk/docs/learned/cli/exec-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Plan Content Extraction (addition to existing doc)

### Reusable Functions

When building exec scripts that work with plan issues, reuse these existing functions rather than reimplementing:

**Location:** `src/erk/cli/commands/exec/scripts/plan_submit_for_review.py`

```python
from erk.cli.commands.exec.scripts.plan_submit_for_review import (
    extract_plan_header_comment_id,
    extract_plan_from_comment,
)
```

**`extract_plan_header_comment_id(issue)`** - Extracts the comment ID containing plan metadata from issue body

**`extract_plan_from_comment(comment)`** - Parses plan content from a GitHub comment

### Common Flow

Both `plan_submit_for_review` and `plan_create_review_branch` use this pattern:

1. Fetch issue via `github_issues.get_issue(number)`
2. Check for `erk-plan` label
3. Extract plan comment ID via `extract_plan_header_comment_id()`
4. Fetch comment via `github_issues.get_comment(comment_id)`
5. Extract plan content via `extract_plan_from_comment()`

### Why This Matters

Reimplementing plan metadata extraction introduces:
- Parsing bugs (the metadata format has edge cases)
- Inconsistent error handling
- Maintenance burden when format changes

Always search for existing plan metadata functions before writing custom extraction.
```

---

#### 3. File write error handling pattern

**Location:** `/home/runner/work/erk/erk/docs/learned/cli/error-handling.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# Exec Script Error Handling

## File Write Operations

When exec scripts write files, catch broad exceptions and wrap in specific error codes:

```python
try:
    # File operations
    plan_file.write_text(plan_content)
    git.commit_ops.stage_files([str(plan_file)])
    git.commit_ops.commit(commit_message)
except Exception as e:
    return MyCommandError(
        success=False,
        error="git_error",  # Specific, machine-readable code
        message=str(e),  # Human-readable details
    )
```

### Why This Pattern

Without wrapping:
- Raw exception messages leak into JSON output
- Subprocess-style errors (exit codes, stderr) break JSON parsing
- Callers can't programmatically handle failures

With wrapping:
- JSON structure is always valid
- Error codes enable programmatic handling
- Messages remain human-readable

### Error Code Guidelines

- Use specific codes: `git_error`, `file_write_error`, `network_error`
- Avoid generic codes: `error`, `failed`, `unknown`
- Include original exception message in `message` field
```

---

## Contradiction Resolutions

No contradictions detected. Existing documentation on branch creation patterns, JSON output handling, and exec command structure is internally consistent. The new command fits cleanly into established patterns.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Gateway Import Path Confusion

**What happened:** Initial import `from erk_shared.gateway.github.abc import GitHubIssues` failed with ImportError.

**Root cause:** Gateway modules are hierarchically organized. GitHubIssues is in `gateway/github/issues/abc.py` submodule, not the main `gateway/github/abc.py` module. The GitHub gateway has separate subgateways for issues, metadata, and pull requests.

**Prevention:** When getting ImportError from gateway imports, check the submodule organization first. The correct import is `from erk_shared.gateway.github.issues.abc import GitHubIssues`.

**Recommendation:** ADD_TO_DOC - Document gateway import hierarchy in architecture docs.

### 2. FakeGit Property Access Mismatch

**What happened:** Test assertion `assert 'PLAN-REVIEW-1234.md' in git.staged_files` returned empty list, causing confusing test failure.

**Root cause:** FakeGit delegates to subgateways - `staged_files` is a property of `commit_ops` subgateway, not the top-level FakeGit class. Accessing at wrong level returns empty list (silent failure).

**Prevention:** Before using FakeGit in tests, check the actual method being called in implementation. Access properties through the same subgateway path as real code (`git.commit_ops.staged_files`).

**Recommendation:** ADD_TO_DOC - Documented above in HIGH priority item #3.

### 3. Directory Creation in File Write Tests

**What happened:** Test using `tmp_path` for repo_root raised FileNotFoundError when writing plan file.

**Root cause:** Tests create path objects but don't always create the directory on filesystem. `pathlib.Path.write_text()` doesn't create parent directories.

**Prevention:** When writing files in tests with tmp_path, always create parent directories explicitly: `repo_root.mkdir(parents=True, exist_ok=True)`.

**Recommendation:** CONTEXT_ONLY - Standard pytest pattern, not project-specific.

## Tripwire Candidates

No items meet the tripwire-worthiness threshold (score >= 4). The patterns discovered are valuable for documentation but don't represent cross-cutting, non-obvious errors that would warrant automatic warnings.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Subgateway property access in FakeGit

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)

The pattern where FakeGit properties like `staged_files` must be accessed via subgateway (`git.commit_ops.staged_files`) rather than top-level is non-obvious. Silent failure (empty list) when accessed wrongly makes debugging difficult. However, this only affects gateway testing code, not cross-cutting across all exec commands.

**Consider promoting if:** Test failures from this pattern become frequent across multiple implementations. Currently only documented as one instance.

### 2. Plan metadata extraction reuse

**Score:** 2/10 (Repeated pattern +1, Cross-cutting +1)

The same metadata extraction flow appears in `plan_submit_for_review` and `plan_create_review_branch`. Reusable functions exist but aren't emphasized in docs. Not HIGH severity since functions exist, but prevents reimplementation across future plan-related commands.

**Consider promoting if:** A third plan-related exec script is implemented without discovering the existing functions, indicating documentation alone isn't sufficient.