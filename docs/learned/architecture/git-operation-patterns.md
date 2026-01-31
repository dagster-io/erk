---
title: Git Operation Patterns
read_when:
  - "implementing git operations in gateways"
  - "checking if git branches or refs exist"
  - "deciding between LBYL and EAFP for git commands"
tripwires:
  - score: 7
    action: "Parsing CalledProcessError messages for git operations"
    warning: "Avoid parsing git error messages to determine failure modes. Use LBYL with git show-ref --verify to check existence before operations, or design discriminated unions that handle all returncode cases explicitly."
    context: "Git error message parsing is fragile (messages can change across versions, localization issues). LBYL with git show-ref is more reliable. For operations with multiple failure modes, use discriminated unions based on returncode patterns."
---

# Git Operation Patterns

## LBYL Pattern: git show-ref --verify

For operations that need to check if a branch or ref exists, use `git show-ref --verify` BEFORE the main operation:

```python
def create_branch(self, *, name: str, start_point: str) -> CreateBranchResult:
    # LBYL: Check if branch already exists
    check_result = run_subprocess(
        ["git", "show-ref", "--verify", f"refs/heads/{name}"],
        cwd=self._cwd,
        capture_output=True,
    )

    if check_result.returncode == 0:
        # Branch exists
        return CreateBranchResult(
            type="branch_already_exists",
            branch_name=name,
        )

    # Branch doesn't exist, proceed with creation
    create_result = run_subprocess(
        ["git", "branch", name, start_point],
        cwd=self._cwd,
        capture_output=True,
    )

    if create_result.returncode == 0:
        return CreateBranchResult(type="success", branch_name=name)

    # Handle unexpected errors
    return CreateBranchResult(
        type="error",
        message=create_result.stderr.decode(),
    )
```

**Why LBYL here:**

- `git show-ref --verify` has a clear returncode contract: 0 = exists, non-zero = doesn't exist
- Avoids parsing error messages like "fatal: A branch named 'foo' already exists"
- More robust across git versions and locales
- Matches erk's LBYL-first philosophy (see AGENTS.md)

## When try/except IS Appropriate

Use try/except for git operations when:

1. **Multiple failure modes**: Operation can fail in several ways, each needs different handling
2. **Atomic operations**: Need to catch unexpected errors (permissions, disk I/O, subprocess failures)

```python
def merge_pr(self, *, pr_number: int, method: str) -> MergePrResult:
    try:
        result = run_subprocess(
            ["gh", "pr", "merge", str(pr_number), f"--{method}"],
            cwd=self._cwd,
            capture_output=True,
        )

        if result.returncode == 0:
            return MergePrResult(type="success", pr_number=pr_number)

        # Parse returncode patterns, NOT error messages
        if "merge conflict" in result.stderr.decode().lower():
            return MergePrResult(type="merge_conflict", pr_number=pr_number)

        if "required status checks" in result.stderr.decode().lower():
            return MergePrResult(type="checks_failing", pr_number=pr_number)

        return MergePrResult(
            type="error",
            message=result.stderr.decode(),
        )

    except Exception as e:
        # Catch subprocess/system failures
        return MergePrResult(type="error", message=str(e))
```

**Why try/except here:**

- Operation is atomic (no pre-check makes sense)
- Multiple failure modes require error message inspection
- Wrapping in try/except catches subprocess and I/O failures

## Anti-Pattern: Error Message Parsing

**Don't do this:**

```python
def create_branch(self, *, name: str, start_point: str) -> CreateBranchResult:
    try:
        result = run_subprocess(["git", "branch", name, start_point], ...)
    except CalledProcessError as e:
        # FRAGILE: Error message can change across git versions
        if "already exists" in e.stderr:
            return CreateBranchResult(type="branch_already_exists", branch_name=name)
        raise
```

**Problems:**

- Error messages can change in new git versions
- Messages may be localized (different languages)
- Brittle string matching
- Violates erk's LBYL principle

**Better approach:**

- Use LBYL with `git show-ref --verify` (as shown above)
- Or use returncode patterns if error messages are unavoidable

## When to Use Each Pattern

| Scenario                             | Pattern                             | Rationale                                       |
| ------------------------------------ | ----------------------------------- | ----------------------------------------------- |
| Branch/ref existence check           | LBYL with `git show-ref --verify`   | Clear returncode contract, no message parsing   |
| Atomic git operation (merge, rebase) | try/except with returncode checking | No meaningful pre-check, multiple failure modes |
| File existence before git operation  | LBYL with `Path.exists()`           | Follows erk's Pathlib-first + LBYL standards    |
| Subprocess failure handling          | try/except in real.py only          | Gateway error boundary pattern                  |

## Related Patterns

- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where try/except belongs in gateways
- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-file checklist
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Designing failure-aware return types
- [Subprocess Wrappers](subprocess-wrappers.md) - Subprocess execution patterns
