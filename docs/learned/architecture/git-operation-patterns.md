---
title: Git Operation Patterns
last_audited: "2026-02-07 20:30 PT"
audit_result: clean
read_when:
  - "implementing git operations in gateways"
  - "checking if git branches or refs exist"
  - "deciding between LBYL and EAFP for git commands"
tripwires:
  - score: 7
    action: "parsing CalledProcessError messages for git operations"
    warning: "Avoid parsing git error messages to determine failure modes. Use LBYL with git show-ref --verify to check existence before operations, or design discriminated unions that handle all returncode cases explicitly."
    context: "Git error message parsing is fragile (messages can change across versions, localization issues). LBYL with git show-ref is more reliable. For operations with multiple failure modes, use discriminated unions based on returncode patterns."
---

# Git Operation Patterns

## The LBYL Principle for Git Operations

Erk's LBYL-first philosophy extends to git operations: **check existence before acting** rather than catching and parsing error messages. This pattern leverages git's stable exit code contracts instead of brittle string matching.

## Why git show-ref --verify Is the Right Check

`git show-ref --verify` has a clear, version-stable returncode contract:

- **returncode 0** = ref exists
- **returncode non-zero** = ref doesn't exist

This is superior to parsing error messages from `git branch` or `git checkout` because:

1. **Immune to localization** — error messages translate, returncodes don't
2. **Stable across versions** — exit codes are API contracts, messages are UI
3. **Single purpose** — explicitly designed for existence checks, not operation side effects
4. **Matches erk's LBYL principle** — check condition first, act second

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py, RealGitBranchOps.create_branch, RealGitBranchOps.delete_branch -->

See `RealGitBranchOps.create_branch()` and `RealGitBranchOps.delete_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py` for the production pattern: both methods use `git show-ref --verify` to check existence before proceeding.

## Decision Framework: LBYL vs Exception Handling

| Scenario                                 | Pattern                           | Rationale                                                         |
| ---------------------------------------- | --------------------------------- | ----------------------------------------------------------------- |
| Branch/ref existence check               | LBYL with `git show-ref --verify` | Clear returncode contract, no message parsing                     |
| Atomic operations (merge, rebase, fetch) | try/except in real.py only        | No meaningful pre-check, multiple failure modes, subprocess risks |
| File existence before git operation      | LBYL with `Path.exists()`         | Follows erk's Pathlib-first + LBYL standards                      |
| Multiple expected failure modes          | Discriminated unions              | Enable caller branching logic on specific error types             |

**Key insight**: LBYL applies when a pre-check is semantically meaningful and actionable. For operations where the check IS the operation (atomic commands like merge), use try/except in real.py only.

## Why Not Parse Error Messages

**WRONG — Error message parsing:**

```python
# DON'T DO THIS
try:
    result = run_subprocess(["git", "branch", name, start_point], ...)
except CalledProcessError as e:
    # FRAGILE: Message can change in new git versions or be localized
    if "already exists" in e.stderr:
        return BranchAlreadyExists(...)
    raise
```

**Problems:**

- Git error messages change across versions (2.30 vs 2.40+ have different phrasing)
- Messages may be localized (`git config core.language`)
- String matching is brittle to minor wording changes
- Violates LBYL: you're catching the operation failure instead of checking first

**RIGHT — Pre-check with stable exit codes:**

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py, RealGitBranchOps.create_branch -->

See `RealGitBranchOps.create_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py`:

The implementation uses `git show-ref --verify refs/heads/{branch_name}` before attempting creation. Returncode 0 means "exists, return BranchAlreadyExists". Non-zero returncode proceeds to creation.

## When Exception Handling IS Appropriate

Gateway methods use try/except **only in real.py** to catch subprocess and system-level failures that cannot be pre-checked. This converts unpredictable runtime errors into structured discriminated unions.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py, BranchCreated, BranchAlreadyExists -->

See `BranchCreated` and `BranchAlreadyExists` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py` for the discriminated union pattern: empty success marker + error type with message field.

**Use try/except in real.py when:**

1. **No meaningful LBYL check exists** — operations like `gh pr merge` can't be pre-validated without actually attempting the merge
2. **Multiple subprocess-level failure modes** — distinguish between "command not found", "permission denied", "merge conflict"
3. **Unpredictable system errors** — disk full, network timeout, process killed

**What to catch:**

- `CalledProcessError` from subprocess commands
- `FileNotFoundError` for missing executables (gh, git)
- `OSError` for system-level failures (permissions, disk space)

**What NOT to catch:**

- Programming errors (`AttributeError`, `TypeError`) — these should crash
- Validation failures that caller should check via LBYL

## The Gateway Error Boundary Pattern

Error handling responsibilities differ by implementation file:

| File          | Error Handling Mechanism                                               | Uses try/except? |
| ------------- | ---------------------------------------------------------------------- | ---------------- |
| `real.py`     | Catches subprocess/system exceptions, converts to discriminated unions | **Yes**          |
| `fake.py`     | Returns error discriminants based on constructor params                | No               |
| `dry_run.py`  | Always returns success discriminants                                   | No               |
| `abc.py`      | Defines return type signatures only                                    | No               |
| `printing.py` | Delegates transparently                                                | No               |

**Why this split?** Real implementations interact with unpredictable external systems. Fake implementations simulate pre-configured failure scenarios for tests. The error boundary belongs at the subprocess interface, not in test infrastructure.

See [Gateway Error Boundaries](gateway-error-boundaries.md) for the complete rationale and implementation patterns.

## Relation to Discriminated Unions

The LBYL pattern with `git show-ref` complements discriminated union error handling:

1. **Pre-check detects expected failures** (branch exists, ref doesn't exist)
2. **Discriminated unions encode these as type-safe return values** (`BranchCreated | BranchAlreadyExists`)
3. **try/except catches unexpected failures** (subprocess crash, git not installed)
4. **Callers use isinstance() checks** for type-safe branching logic

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py, RealGitBranchOps.create_branch -->

Example flow in `RealGitBranchOps.create_branch()`:

- LBYL check with `git show-ref` detects "branch exists" → return `BranchAlreadyExists`
- Creation attempt via subprocess (wrapped in try/except in real.py's caller context)
- Success → return `BranchCreated`
- Unexpected failure (process crash) → try/except converts to `RuntimeError`

## Related Patterns

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — When to use unions vs exceptions, pattern structure
- [Gateway Error Boundaries](gateway-error-boundaries.md) — Where try/except belongs in the 5-file gateway pattern
- [Subprocess Wrappers](subprocess-wrappers.md) — Using `run_subprocess_with_context()` correctly
