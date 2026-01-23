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

## Graceful Degradation Exit Pattern

Exec scripts that may be called with `|| true` safety nets (common in CI/workflow contexts) must follow a graceful degradation contract:

### Requirements

1. **Always exit 0**: Never exit with non-zero codes, even for validation failures
2. **Return structured JSON errors**: Include `success: false` and descriptive error fields
3. **Fail fast**: Validate preconditions before expensive operations (network calls, context initialization)

### Why Exit 0?

Exec scripts are often invoked in workflow contexts like:

```bash
erk exec impl-signal started --session-id "$SESSION_ID" || true
```

If the script exits non-zero, the `|| true` silently swallows the error. By exiting 0 with a JSON error response, callers can parse the response and handle failures appropriately.

### Error Response Structure

```json
{
  "success": false,
  "error_type": "<error-category>",
  "message": "<human-readable description>"
}
```

### Example: impl-signal Validation

```python
if not session_id or not session_id.strip():
    return json.dumps({
        "success": False,
        "event": "started",
        "error_type": "session-id-required",
        "message": "Session ID required for impl-signal started."
    })
    # Note: Function returns normally (exit 0), not sys.exit(1)
```

This differs from typical CLI error handling where non-zero exits indicate failure. For exec scripts in workflow contexts, exit 0 + JSON error response enables proper error handling by callers.

## Implementation Reference

See `src/erk/cli/commands/exec/scripts/handle_no_changes.py` for the canonical implementation of PR body generation patterns.

See `src/erk/cli/commands/exec/scripts/impl_signal.py` for the canonical implementation of graceful degradation and validation patterns.

## Related Topics

- [erk exec Commands](erk-exec-commands.md) - Command reference
- [No Code Changes Handling](../planning/no-changes-handling.md) - Example use case
