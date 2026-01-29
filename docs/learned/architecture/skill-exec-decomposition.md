---
title: Skill-Exec Decomposition Pattern
read_when:
  - "creating a multi-step agent command"
  - "deciding whether to use exec commands or inline logic in a skill"
  - "understanding how skills compose exec commands"
  - "designing agent workflows with multiple operations"
---

# Skill-Exec Decomposition Pattern

Skills orchestrate user-facing workflows by composing atomic `erk exec` commands. This decomposition separates concerns: exec commands implement single, testable operations; skills handle user interaction, error formatting, and command sequencing.

## Pattern Overview

**Architecture**:

```
User → Slash Command (/erk:review-plan)
         ↓
      Skill (.claude/commands/erk/review-plan.md)
         ↓
      erk exec Commands (plan-create-review-branch, etc.)
         ↓
      Gateway Abstractions (Git, GitHub, Time)
```

**Responsibilities by layer**:

| Layer            | Responsibility                                        | Examples                                                |
| ---------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| **Skill**        | User interaction, command chaining, output formatting | Parse args, ask user questions, format success messages |
| **Exec Command** | Atomic operation, typed errors, JSON output           | Create branch, create PR, update metadata               |
| **Gateway**      | Platform abstraction, dry-run support                 | Git operations, GitHub API calls                        |

## When to Decompose vs. Implement Monolithically

### Decompose into exec commands when:

1. **Operation is reusable**: Multiple workflows need the same operation
2. **Operation needs testing**: Atomic operation benefits from isolated tests with fakes
3. **Operation has typed error states**: Different failure modes need specific error codes
4. **Operation mutates external state**: Git, GitHub, filesystem operations

**Example**: `plan-create-review-branch` is reusable, testable, has typed errors (issue_not_found, branch_exists), and mutates git state.

### Keep inline in skill when:

1. **Operation is skill-specific**: Only this workflow needs it
2. **Operation is pure UI logic**: Formatting output, asking questions
3. **Operation is trivial**: Single bash command with no error handling

**Example**: Formatting the success message in `/erk:review-plan` stays inline—it's presentation logic specific to that command.

## JSON-Based IPC

Exec commands return structured JSON for reliable parsing:

### Success Response Pattern

```json
{
  "success": true,
  "issue_number": 1234,
  "branch": "plan-review-1234-01-15-1430",
  "file_path": "PLAN-REVIEW-1234.md",
  "plan_title": "Add Feature X"
}
```

### Error Response Pattern

```json
{
  "success": false,
  "error": "issue_not_found",
  "message": "Issue #1234 not found"
}
```

**Skill parsing**:

```bash
RESULT=$(erk exec plan-create-review-branch 1234)
SUCCESS=$(echo "$RESULT" | jq -r '.success')

if [ "$SUCCESS" = "true" ]; then
  BRANCH=$(echo "$RESULT" | jq -r '.branch')
  echo "Created branch: $BRANCH"
else
  ERROR=$(echo "$RESULT" | jq -r '.error')
  MESSAGE=$(echo "$RESULT" | jq -r '.message')
  echo "Error [$ERROR]: $MESSAGE"
  exit 1
fi
```

## Error Handling

### Typed Error Codes at Exec Level

Exec commands use frozen dataclass exceptions with error codes:

```python
@dataclass(frozen=True)
class CreateReviewPRError:
    success: bool
    error: str  # Typed error code
    message: str  # Human-readable message

class CreateReviewPRException(Exception):
    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
```

**Error codes are typed strings**, not enums, for JSON serialization:

- `issue_not_found`
- `pr_already_exists`
- `invalid_issue`
- `branch_exists`

### User-Friendly Messages at Skill Level

Skills translate error codes into user-facing guidance:

```bash
ERROR=$(echo "$RESULT" | jq -r '.error')

case "$ERROR" in
  issue_not_found)
    echo "Error: Issue #$ISSUE not found"
    echo "Check the issue number and try again."
    ;;
  missing_erk_plan_label)
    echo "Error: Issue #$ISSUE is not an erk-plan"
    echo "Only saved plans can be reviewed. Run /erk:plan-save first."
    ;;
  pr_already_exists)
    echo "Error: A review PR already exists for this plan"
    echo "View it with: gh pr view ..."
    ;;
esac
```

**Why this separation**: Exec commands focus on operation logic, skills focus on user experience.

## Canonical Example: /erk:review-plan

The `/erk:review-plan` skill orchestrates 4 exec commands to create a plan review PR.

**Source**: `.claude/commands/erk/review-plan.md` (118 lines)

### Command Flow

```
1. User invokes: /erk:review-plan 1234

2. Skill: Parse argument (issue number)

3. Skill: Check for existing review
   ├─> erk exec get-plan-metadata 1234 review_pr
   └─> If exists: display and exit

4. Skill: Save current branch
   └─> git branch --show-current

5. Skill: Create review branch
   ├─> erk exec plan-create-review-branch 1234
   ├─> Parse: branch, file_path, plan_title
   └─> Handle errors: issue_not_found, no_plan_content

6. Skill: Create review PR
   ├─> erk exec plan-create-review-pr 1234 <branch> <title>
   ├─> Parse: pr_number, pr_url
   └─> Handle errors: pr_already_exists, invalid_issue

7. Skill: Display success message
   └─> Format PR URL, next steps

8. Skill: Return to original branch
   └─> git checkout <original_branch>
```

### Why 4 Commands Instead of 1?

Each command is **independently useful**:

- `get-plan-metadata`: Read any metadata field from any plan
- `plan-create-review-branch`: Create branch without PR (for manual workflow)
- `plan-create-review-pr`: Create PR for existing branch (retry after failure)

**Monolithic alternative would**:

- Duplicate logic across workflows
- Make testing harder (mocking entire flow vs. atomic ops)
- Reduce reusability

## Testing Strategy

### Exec Commands: Unit Tests with Fakes

Test exec commands via gateway fakes:

```python
def test_plan_create_review_pr_duplicate_detection():
    # Arrange: Fake GitHub returns existing PR
    fake_github = FakeGitHub()
    fake_github.set_pr_for_branch("plan-review-123", pr_number=456)

    # Act: Try to create PR
    with pytest.raises(CreateReviewPRException) as exc_info:
        _create_review_pr_impl(fake_github, ...)

    # Assert: Correct error code
    assert exc_info.value.error == "pr_already_exists"
```

**Benefits**:

- Fast (no real GitHub calls)
- Deterministic (no network flakiness)
- Tests all error paths easily

### Skills: Integration Tests

Test skills via subprocess execution:

```bash
# Run skill via Claude Code
OUTPUT=$(.claude/commands/erk/review-plan.md 1234)

# Verify success message appears
echo "$OUTPUT" | grep "Plan #1234 submitted for review"
```

Or delegate to agents:

- Task agent runs skill
- Verify expected bash commands executed
- Check output formatting

## Implementation Checklist

When creating a new multi-step workflow:

1. **Identify atomic operations**: What are the independent, testable steps?
2. **Create exec commands**: One per atomic operation, with typed errors
3. **Test exec commands**: Unit tests with fakes for each error path
4. **Create skill**: Chain exec commands, handle UI logic
5. **Document both**: Exec commands in `erk-exec-commands.md`, skill workflow in command file

## Anti-Patterns

### ❌ Inline Git/GitHub Operations in Skills

```bash
# WRONG: Git operations directly in skill
git fetch origin
git checkout -b "plan-review-$ISSUE-$(date +%m-%d-%H%M)"
git push -u origin HEAD
```

**Problem**: Not testable, no dry-run support, error handling inconsistent.

**Fix**: Use `erk exec plan-create-review-branch $ISSUE`

### ❌ Putting User Interaction in Exec Commands

```python
# WRONG: Prompting user in exec command
if existing_pr:
    answer = input("PR exists. Create anyway? (y/n): ")
    if answer != "y":
        return
```

**Problem**: Breaks non-interactive workflows, testing requires mocking input.

**Fix**: Return error code, let skill handle user interaction.

### ❌ Parsing Output with Regex

```bash
# WRONG: Parsing text output
BRANCH=$(echo "$OUTPUT" | grep "Created branch:" | cut -d' ' -f3)
```

**Problem**: Fragile, breaks if output format changes.

**Fix**: Return JSON, parse with `jq`:

```bash
BRANCH=$(echo "$OUTPUT" | jq -r '.branch')
```

## Related Topics

- [PR-Based Plan Review Workflow](../planning/pr-review-workflow.md) - Example workflow using this pattern
- [erk exec Commands Reference](../cli/erk-exec-commands.md) - All available exec commands
- [PR Operations](../cli/pr-operations.md) - PR creation patterns used in exec commands
- [Gateway ABC Implementation](gateway-abc-implementation.md) - How exec commands use gateways
