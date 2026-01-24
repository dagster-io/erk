# Plan: Add Plan/Objective Context to PR Summary Generation

## Problem

When `erk pr summarize` and `erk pr submit` generate PR descriptions, they only pass the diff and branch names to Claude. The AI must guess the rationale for changes, leading to incorrect summaries.

**Example**: Plan says "--verbose is required because of CLI validation error with stream-json format" but PR summary incorrectly said "--verbose improves observability".

## Solution

Pass the linked plan content to the commit message generator so Claude understands the **why** behind changes, not just the **what**.

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/core/plan_context_provider.py` | **NEW** - PlanContext dataclass + PlanContextProvider service |
| `src/erk/core/commit_message_generator.py` | Add `plan_context` to request, update prompt building |
| `src/erk/cli/commands/pr/shared.py` | Add `plan_context` parameter to `run_commit_message_generation()` |
| `src/erk/cli/commands/pr/summarize_cmd.py` | Fetch and pass plan context |
| `src/erk/cli/commands/pr/submit_cmd.py` | Fetch and pass plan context |
| `tests/core/test_plan_context_provider.py` | **NEW** - Unit tests for provider |
| `tests/core/test_commit_message_generator.py` | Add tests for plan context in prompt |

## Implementation Steps

### Step 1: Create PlanContextProvider

New file: `src/erk/core/plan_context_provider.py`

```python
@dataclass(frozen=True)
class PlanContext:
    """Context from an erk-plan issue for PR generation."""
    issue_number: int
    plan_content: str
    objective_summary: str | None  # e.g., "Objective #123: Improve CI reliability"


class PlanContextProvider:
    """Provides plan context for branches linked to erk-plan issues."""

    def __init__(self, github_issues: GitHubIssues) -> None:
        self._github_issues = github_issues

    def get_plan_context(
        self,
        repo_root: Path,
        branch_name: str,
    ) -> PlanContext | None:
        """Get plan context for a branch, if available."""
        # 1. Extract issue number from branch (P5763-fix-... -> 5763)
        # 2. Fetch issue body
        # 3. Extract plan_comment_id from metadata
        # 4. Fetch comment and extract plan content
        # 5. Optionally get objective title if linked
        # Returns None on any failure (graceful degradation)
```

Key dependencies:
- `extract_leading_issue_number()` from `erk_shared.naming`
- `extract_plan_header_comment_id()` from `erk_shared.github.metadata.plan_header`
- `extract_plan_from_comment()` from same module
- `extract_plan_header_objective_issue()` from same module

### Step 2: Update CommitMessageRequest

In `src/erk/core/commit_message_generator.py`:

```python
@dataclass(frozen=True)
class CommitMessageRequest:
    diff_file: Path
    repo_root: Path
    current_branch: str
    parent_branch: str
    commit_messages: list[str] | None
    plan_context: PlanContext | None  # NEW - follows existing pattern
```

### Step 3: Update prompt building

In `_build_context_section()`, add plan context section:

```markdown
## Implementation Plan (Issue #5763)

The following plan describes the intent and rationale for these changes:

[plan content here]

### Parent Objective
Objective #100: Improve CI reliability

Use this plan as the primary source of truth for understanding WHY changes were made.
```

### Step 4: Update shared.py

Add `plan_context` parameter to `run_commit_message_generation()`:

```python
def run_commit_message_generation(
    *,
    generator: CommitMessageGenerator,
    diff_file: Path,
    repo_root: Path,
    current_branch: str,
    parent_branch: str,
    commit_messages: list[str] | None,
    plan_context: PlanContext | None,  # NEW
    debug: bool,
) -> CommitMessageResult:
```

### Step 5: Update callers

In both `summarize_cmd.py` and `submit_cmd.py`:

```python
# Create provider
plan_provider = PlanContextProvider(ctx.github_issues)

# Fetch plan context (returns None if branch not linked to plan)
plan_context = plan_provider.get_plan_context(repo_root, current_branch)

# Pass to generator
msg_result = run_commit_message_generation(
    ...
    plan_context=plan_context,
    ...
)
```

## Error Handling Strategy

Plan fetch failures should **not** block PR generation:
- If branch has no issue number prefix -> `None`
- If issue doesn't exist or API error -> `None`
- If no plan_comment_id in metadata -> `None`
- If comment fetch fails -> `None`

This maintains backward compatibility for non-plan branches.

## Testing Strategy

### Unit tests for PlanContextProvider
- Test branch name parsing (P-prefixed, legacy, no prefix)
- Test successful plan content extraction with FakeGitHubIssues
- Test graceful degradation on missing issue, missing comment, etc.

### Unit tests for CommitMessageGenerator
- Verify plan content appears in prompt via `executor.prompt_calls`
- Test with and without plan context
- Test objective summary inclusion

## Verification

1. Run `erk pr summarize` on a branch linked to a plan issue
2. Check that the generated summary incorporates plan rationale
3. Run on a non-plan branch - should work without plan context
4. Run tests: `make test` (unit tests include new tests)