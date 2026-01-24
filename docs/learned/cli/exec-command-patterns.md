---
title: Exec Command Patterns
read_when:
  - "writing exec scripts with PR/issue output"
  - "building diagnostic messages"
  - "standardizing exec command output"
tripwires:
  - action: "writing PR/issue body generation in exec scripts"
    warning: "Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability."
---

# Exec Command Patterns

Patterns for writing `erk exec` scripts that produce user-facing output like PR bodies and issue comments.

## Diagnostic PR Body Generation

When exec scripts need to update PR bodies with diagnostic information, follow the `_build_pr_body()` pattern:

**Key principles:**

1. **Structured sections**: Use clear markdown headers (##, ###)
2. **Actionable guidance**: Include "Next Steps" with numbered actions
3. **Cross-linking**: Reference related issues/PRs with GitHub links
4. **Optional context**: Handle optional fields gracefully (workflow URLs, commit lists)

**Section structure:**

```markdown
## [Status Header]

[Brief explanation of what happened]

### Diagnosis

[Root cause analysis with context]

### Next Steps

1. [First action]
2. [Second action]
3. [Third action]

---

Closes #[issue_number]

[Optional: workflow run link]
```

## Issue Notification Comments

When notifying issues about related PRs or events, follow the `_build_issue_comment()` pattern:

**Key principles:**

1. **Concise**: One or two sentences describing the event
2. **Linked**: Include PR/issue references
3. **Actionable**: Tell user what to do next

**Example format:**

```
Implementation produced no code changes. See PR #123 for diagnostic information.

If the work is already complete, close both this issue and the PR.
```

## Testability Patterns

Structure body generation as pure functions:

- Accept all data as parameters (no I/O in the function)
- Return formatted string
- Easy to unit test with various inputs

**Example signature:**

```python
def _build_pr_body(
    *,
    issue_number: int,
    behind_count: int,
    base_branch: str,
    recent_commits: str | None,
    run_url: str | None,
) -> str:
```

## Implementation Reference

See `src/erk/cli/commands/exec/scripts/handle_no_changes.py` for the canonical implementation of these patterns.

## Graceful Degradation for Optional Parameters

Some exec scripts accept optional parameters that may not be available in all contexts. Use graceful degradation to avoid blocking workflows.

### Pattern: Optional Session ID

```python
def validate_session_id(session_id: str | None) -> str | None:
    """Validate session ID with graceful degradation.

    Returns None if session ID is missing/invalid, allowing
    the workflow to continue with reduced functionality.
    """
    if session_id is None:
        return None
    if not session_id.strip():
        return None
    return session_id

# Usage in command
session_id = validate_session_id(ctx.params.get("session_id"))
if session_id is None:
    # Continue without session tracking
    output["session_tracked"] = False
else:
    # Track with session ID
    output["session_tracked"] = True
```

### When to Use

- Session IDs in hooks (may not be available in all invocation contexts)
- Optional metadata that enriches but doesn't block functionality
- Parameters passed through `|| true` shell patterns

## Dual Input Handling

Some exec commands accept input from either a file or stdin. This pattern enables both scripted (piped) and direct (file path) usage.

### Pattern: --plan-file Option

```python
@click.command(name="validate-plan-content")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to plan file. If not provided, reads from stdin.",
)
def validate_plan_content(*, plan_file: Path | None) -> None:
    # Read from file or stdin
    if plan_file:
        content = plan_file.read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    # Process content...
```

### Usage Examples

```bash
# Pipe from another command (stdin)
echo "$plan" | erk exec validate-plan-content

# Read from file (--plan-file)
erk exec validate-plan-content --plan-file ./plan.md
```

### Key Principles

1. **File option is optional** - stdin is the default input
2. **Use `Path | None`** - Type hint reflects optionality
3. **`exists=True` for file** - Click validates file exists before command runs
4. **Document both modes** - Show pipe and file examples in docstring

### When to Use

- Commands that process content (plans, prompts, logs)
- Commands called both interactively and in pipelines
- Commands where input may come from files or generated content

### Reference Implementation

See `src/erk/cli/commands/exec/scripts/validate_plan_content.py`.

## Related Topics

- [erk exec Commands](erk-exec-commands.md) - Command reference
- [No Code Changes Handling](../planning/no-changes-handling.md) - Example use case
