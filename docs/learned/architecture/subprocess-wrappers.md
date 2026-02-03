---
title: Subprocess Wrappers
read_when:
  - "using subprocess wrappers"
  - "executing shell commands"
  - "understanding subprocess patterns"
tripwires:
  - action: "using bare subprocess.run with check=True"
    warning: "Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations."
---

# Subprocess Execution Wrappers

**NEVER use bare `subprocess.run(..., check=True)`. ALWAYS use wrapper functions.**

This guide explains the two-layer pattern for subprocess execution in erk: gateway layer and CLI layer wrappers.

## Scope

**These rules apply to production erk code** in `src/erk/` and `packages/erk-shared/`.

**Exception: erk-dev** (`packages/erk-dev/`) is developer tooling and is exempt from these rules. Direct `subprocess.run` is acceptable in erk-dev commands since they don't need the testability/dry-run benefits of wrapper functions.

## Two-Layer Pattern

Erk uses a two-layer design for subprocess execution to provide consistent error handling across different boundaries:

- **Gateway layer**: `run_subprocess_with_context()` - Raises RuntimeError for business logic
- **CLI layer**: `run_with_error_reporting()` - Prints user-friendly message and raises SystemExit

## Wrapper Functions

### run_subprocess_with_context (Gateway Layer)

**When to use**: In business logic, gateway classes, and core functionality that may be called from multiple contexts.

**Import**: `from erk.core.subprocess import run_subprocess_with_context`

**Behavior**: Raises `RuntimeError` with rich context on failure

**Example**:

```python
from erk.core.subprocess import run_subprocess_with_context

# ✅ CORRECT: Rich error context with stderr
result = run_subprocess_with_context(
    ["git", "worktree", "add", str(path), branch],
    operation_context=f"add worktree for branch '{branch}' at {path}",
    cwd=repo_root,
)
```

**Why use this**:

- **Rich error messages**: Includes operation context, command, exit code, stderr
- **Exception chaining**: Preserves original CalledProcessError for debugging
- **Testable**: Can be caught and handled in tests

### run_with_error_reporting (CLI Layer)

**When to use**: In CLI command handlers where you want to immediately exit on failure with a user-friendly message.

**Import**: `from erk.cli.subprocess_utils import run_with_error_reporting`

**Behavior**: Prints error message to stderr and raises `SystemExit` on failure

**Example**:

```python
from erk.cli.subprocess_utils import run_with_error_reporting

# ✅ CORRECT: User-friendly error messages + SystemExit
run_with_error_reporting(
    ["gh", "pr", "view", str(pr_number)],
    operation_context="view pull request",
    cwd=repo_root,
)
```

**Why use this**:

- **User-friendly**: Error messages are clear and actionable
- **CLI semantics**: Exits immediately with non-zero code
- **No exception handling needed**: Wrapper handles everything

## Why This Matters

- **Rich error messages**: Both wrappers include operation context, command, exit code, and stderr
- **Exception chaining**: Preserves original CalledProcessError for debugging
- **Consistent patterns**: Two clear boundaries with appropriate error handling
- **Debugging support**: Full context available in error messages and logs

## LBYL Patterns to Keep

**DO NOT migrate check=False LBYL patterns** - these are intentional:

```python
# ✅ CORRECT: Intentional LBYL pattern (keep as-is)
result = subprocess.run(cmd, check=False, capture_output=True, text=True)
if result.returncode != 0:
    return None  # Graceful degradation
```

When code explicitly uses `check=False` and checks the return code, this is a Look Before You Leap (LBYL) pattern for graceful degradation. Do not refactor these to use wrappers.

## Graceful Degradation Pattern

Not all subprocess calls should use `run_with_error_reporting()`. Use explicit exception handling when:

1. **The operation is optional** - Failure should not stop the main workflow
2. **Fire-and-forget semantics** - The result is informational, not critical
3. **Warning vs Error** - You want to show a warning and continue, not exit

### Example: Async Learn Trigger in Land Command

```python
# Pattern: check=True with explicit CalledProcessError handling
try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    # Handle success
except subprocess.CalledProcessError as e:
    # Show warning, continue execution
    user_output(click.style("⚠ ", fg="yellow") + f"Optional operation failed: {e}")
except FileNotFoundError:
    # Handle missing command gracefully
    user_output(click.style("⚠ ", fg="yellow") + "Command not found")
```

### Decision Table

| Scenario                       | Pattern                         | Reason                           |
| ------------------------------ | ------------------------------- | -------------------------------- |
| CLI command that must succeed  | `run_with_error_reporting()`    | SystemExit on failure is correct |
| Optional background operation  | Explicit exception handling     | Main operation should continue   |
| Gateway real.py implementation | `run_subprocess_with_context()` | Consistent error wrapping        |

## GitHub API Commands with Retry

For GitHub API commands that may fail due to transient network errors, use `execute_gh_command_with_retry()`:

```python
from erk_shared.subprocess_utils import execute_gh_command_with_retry

result = execute_gh_command_with_retry(cmd, cwd, time_impl)
```

This builds on `run_subprocess_with_context()` and adds:

- Automatic retry on transient errors (network timeouts, connection failures)
- Exponential backoff delays (0.5s, 1.0s by default)
- Time injection for testability

See [GitHub API Retry Mechanism](github-api-retry-mechanism.md) for the full pattern.

## Error Accumulation Pattern

When streaming stdout line-by-line with `subprocess.Popen()`, stderr must be captured in a background thread to avoid deadlock. This pattern is used in `ClaudePromptExecutor.execute_command_streaming()`.

### Why Background Thread for Stderr?

The problem:

1. Process writes to both stdout and stderr
2. Main thread blocks on `for line in process.stdout`
3. If stderr buffer fills, process blocks waiting for it to drain
4. Deadlock: main thread waits for stdout, process waits for stderr

The solution:

```
Main Thread                          Background Thread
───────────────────────────────      ──────────────────────────
process = Popen(stdout=PIPE,
                stderr=PIPE)
                                     for line in process.stderr:
for line in process.stdout:              stderr_parts.append(line)
    yield parse_event(line)

process.wait()
stderr_thread.join(timeout=5.0)
# Use accumulated stderr in error msg
```

### Implementation Notes

- Use `daemon=True` so thread doesn't prevent process exit
- Use a timeout on `join()` to avoid hanging on pathological cases
- Stderr is accumulated as list, joined only when needed for error message
- See `src/erk/core/prompt_executor.py` for the canonical implementation

### When to Use This Pattern

- Streaming stdout with `Popen(stdout=PIPE)` while also capturing stderr
- Long-running processes where stderr could fill its buffer
- Real-time event processing that must not block

### When NOT to Use This Pattern

- Simple `subprocess.run(capture_output=True)` - handles this automatically
- Fire-and-forget processes where stderr is ignored
- Short-lived commands that complete quickly

## Temporary File Lifecycle Pattern in Shell

When passing large or formatted content to external CLI tools (like `gh pr comment`), use the standard Unix temp file pattern to avoid command-line argument limits and escape sequence issues.

### The Pattern

```bash
# 1. Create temp file
TEMP_FILE=$(mktemp)

# 2. Write content with proper formatting
printf "%b\n" "$CONTENT" > "$TEMP_FILE"

# 3. Pass filename to command
gh pr comment "$PR_NUMBER" --body-file "$TEMP_FILE"

# 4. Cleanup
rm "$TEMP_FILE"
```

### Why This Pattern?

1. **Bypasses ARG_MAX**: Linux kernel limits command-line argument length to ~2MB. File I/O has no such limit.
2. **Reliable escape sequences**: `printf "%b"` is POSIX standard for interpreting backslash escape sequences (`\n`, `\t`, etc.).
3. **Clean resource management**: Explicit cleanup prevents temp file accumulation.

### When to Use

- GitHub Actions workflows posting CI outputs (rebase logs, test results)
- Any CLI tool accepting file-based input (`--body-file`, `--input-file`, etc.)
- Content that could potentially be large (>1KB as rule of thumb)
- Multi-line content with escape sequences

### Real-World Example

From `.github/workflows/pr-fix-conflicts.yml`:

```yaml
BODY="## Conflict Resolution Failed\n\nRebase output:\n\`\`\`\n$REBASE_OUTPUT\n\`\`\`"
TEMP_FILE=$(mktemp)
printf "%b\n" "$BODY" > "$TEMP_FILE"
gh pr comment "$PR_NUMBER" --body-file "$TEMP_FILE"
rm "$TEMP_FILE"
```

This pattern is especially important in CI where large content is common and shell behavior differs from local development (GitHub Actions uses dash/sh, not bash).

### See Also

- [GitHub CLI PR Comment Patterns](../ci/github-cli-comment-patterns.md) - Full guide to CI comment posting patterns
- [GitHub Actions Output Patterns](../ci/github-actions-output-patterns.md) - For `$GITHUB_OUTPUT` (different context)

## Lenient vs. Strict Handlers

Some subprocess operations should fail gracefully while others should fail fast. The `_get_pr_for_plan_direct()` pattern from `trigger-async-learn` demonstrates the lenient approach.

### Decision Matrix

| Aspect                    | Lenient Handler                        | Strict Handler                         |
| ------------------------- | -------------------------------------- | -------------------------------------- |
| **Error handling**        | Returns `None` on any failure          | Raises exception or returns error type |
| **Return type**           | `T \| None`                            | `T` or discriminated union             |
| **Use case**              | Optional operations, fail-open         | Critical operations, fail-closed       |
| **Caller responsibility** | Check for `None`, decide how to handle | Catch exception or check error type    |

### Lenient Pattern

Use when the operation is **optional** and the caller should decide how to handle absence:

See `_get_pr_for_plan_direct()` in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py:212-257`.

```python
# Signature and return type (see source for full implementation):
def _get_pr_for_plan_direct(
    *, github_issues, github, repo_root: Path, issue_number: int,
) -> dict[str, object] | None:
    # Returns None on ANY failure: missing issue, metadata, branch, or PR
```

**Characteristics:**

- **No exceptions** - Never raises, always returns `None` on failure
- **No error messages** - Caller decides what to log
- **Uniform failure** - All failure modes return `None` consistently

**When to use:**

- Background operations that shouldn't block main workflow
- Optional data fetching (e.g., review comments for learn)
- Exploratory queries where absence is expected

### Strict Pattern

Use when the operation is **critical** and failure should be explicit:

See `get_pr_for_plan()` in `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py:60-122`.

```python
# Signature (see source for full implementation):
def get_pr_for_plan(
    *, ctx: ErkContext, repo_root: Path, issue_number: int,
) -> int:
    # Raises ValueError on ANY failure; attempts branch_name recovery via pattern matching
```

**Characteristics:**

- **Explicit errors** - Each failure mode has specific error message
- **Recovery attempts** - May try to infer missing data before failing
- **Clear contract** - Caller knows exceptions mean critical failure

**When to use:**

- User-facing commands where failure needs explanation
- Critical path operations that cannot continue without the data
- CLI commands that should exit with error message

### Real-World Example: trigger-async-learn

The `trigger-async-learn` command uses **lenient handler** for PR lookup:

```python
# Lenient: Try to get PR info, but don't fail if unavailable
pr_info = _get_pr_for_plan_direct(...)
if pr_info is None:
    # No PR found - that's OK, just skip review comments
    click.echo("No PR found for plan, skipping review comments", err=True)
    review_comments = None
else:
    # PR found - fetch review comments
    pr_number = pr_info["pr_number"]
    review_comments = fetch_review_comments(repo_root, pr_number)

# Continue with learn workflow (with or without review comments)
upload_materials(sessions, review_comments)
trigger_workflow(...)
```

**Why lenient?**

- Learn can succeed without review comments
- PR might not exist yet (plan created before implementation)
- Running from GitHub Actions (no current branch for recovery)

**Contrast with strict handler:**

The same PR lookup in `get_pr_for_plan.py` is **strict** because it's a user-facing command where the user explicitly asked for the PR and expects either the answer or a clear error message.

### See Also

- [Fail-Open Patterns](fail-open-patterns.md) - When to allow graceful degradation
- [Branch Name Inference](../planning/branch-name-inference.md) - Recovery mechanism for missing branch_name

## Summary

- **Gateway layer**: Use `run_subprocess_with_context()` for business logic
- **CLI layer**: Use `run_with_error_reporting()` for command handlers
- **GitHub with retry**: Use `execute_gh_command_with_retry()` for network-sensitive operations
- **Streaming with stderr**: Use background thread accumulation pattern
- **Temp file pattern**: Use `mktemp` → `printf "%b"` → file-based input → `rm` for large/formatted content
- **Keep LBYL**: Don't migrate intentional `check=False` patterns
- **Never use bare check=True**: Always use one of the wrapper functions
