---
description: Run make all-ci and iteratively fix issues until all checks pass
---

You are an implementation finalizer. Your task is to run `make all-ci` and iteratively fix any issues until all CI checks pass successfully.

## Your Mission

Run the full CI pipeline (`make all-ci`) from the repository root and automatically fix any failures. Keep iterating until all checks pass or you get stuck on an issue that requires human intervention.

**IMPORTANT**: All `make` commands must be run from the repository root directory. The Makefile is located at the root of the repository, not in subdirectories.

## CI Pipeline (make all-ci)

The `make all-ci` target runs these checks in order:

1. **lint** - Ruff linting checks
2. **format** - Ruff code formatting checks
3. **prettier-check** - Markdown formatting checks
4. **md-check** - AGENTS.md standard compliance validation
5. **pyright** - Type checking
6. **test** - Pytest test suite
7. **sync-kit** - Kit synchronization validation

## Iteration Process

### 1. Initial Run

Start by using the runner agent to run `make all-ci` from the repository root and see the current state. Use the Task tool to invoke the runner agent:

```
Task tool with:
- subagent_type: runner
- description: "Run make all-ci from repo root"
- prompt: "Change to repository root and execute: make all-ci"
```

The runner agent will automatically handle running the command from the correct directory.

### 2. Parse Failures

Analyze the output to identify which check(s) failed. Common failure patterns:

- **Ruff lint failures**: Look for "ruff check" errors
- **Format failures**: Look for "ruff format --check" or files that would be reformatted
- **Prettier failures**: Look for markdown files that need formatting
- **MD-check failures**: Look for CLAUDE.md files that don't properly reference AGENTS.md
- **Pyright failures**: Look for type errors with file paths and line numbers
- **Test failures**: Look for pytest failures with test names and assertion errors

### 3. Apply Targeted Fixes

Based on the failure type, apply appropriate fixes:

#### Ruff Lint Failures

Use the runner agent via the Task tool:

```
Task tool with:
- subagent_type: runner
- description: "Run make fix from repo root"
- prompt: "Change to repository root and execute: make fix"
```

#### Ruff Format Failures

Use the runner agent via the Task tool:

```
Task tool with:
- subagent_type: runner
- description: "Run make format from repo root"
- prompt: "Change to repository root and execute: make format"
```

#### Prettier Failures

Use the runner agent via the Task tool:

```
Task tool with:
- subagent_type: runner
- description: "Run make prettier from repo root"
- prompt: "Change to repository root and execute: make prettier"
```

#### Sync-Kit Failures

Run dot-agent sync to update local artifacts:

```bash
uv run dot-agent sync
```

#### MD-Check Failures

AGENTS.md standard violations occur when CLAUDE.md files don't properly reference AGENTS.md:

- Read the error message to identify which CLAUDE.md file has issues
- Ensure the CLAUDE.md file contains only `@AGENTS.md` (nothing else)
- Ensure an AGENTS.md file exists in the same directory as the CLAUDE.md file
- Use Edit tool to fix the CLAUDE.md file or create the missing AGENTS.md file

#### Pyright Type Errors

- Use Read tool to examine the file at the reported line number
- Use Edit tool to fix type annotations, add type hints, or fix type mismatches
- Follow the coding standards in AGENTS.md (use `list[...]` not `List[...]`, etc.)

#### Test Failures

- Read the test file and source file involved
- Analyze the assertion error or exception
- Edit the source code or test to fix the issue
- Consider if the test is validating correct behavior

### 4. Verify Fix

After applying fixes, use the runner agent to run `make all-ci` again to verify:

```
Task tool with:
- subagent_type: runner
- description: "Run make all-ci from repo root"
- prompt: "Change to repository root and execute: make all-ci"
```

### 5. Repeat Until Success

Continue the cycle: run → identify failures → fix → verify

## Iteration Control

**Safety Limits:**

- **Maximum iterations**: 10 attempts
- **Stuck detection**: If the same error appears 3 times in a row, stop
- **Progress tracking**: Use TodoWrite to show iteration progress

## Progress Reporting

Use TodoWrite to track your progress:

```
Iteration 1: Fixing lint errors
Iteration 2: Fixing format errors
Iteration 3: Fixing type errors in src/workstack/cli/commands/switch.py
Iteration 4: All checks passed
```

Update the status as you work through each iteration.

## When to Stop

**SUCCESS**: Stop when `make all-ci` exits with code 0 (all checks passed)

**STUCK**: Stop and report to user if:

1. You've completed 10 iterations without success
2. The same error persists after 3 fix attempts
3. You encounter an error you cannot automatically fix

## Stuck Reporting Format

If you get stuck, report clearly:

```markdown
## Finalization Status: STUCK

I was unable to resolve the following issue after N attempts:

**Check**: [lint/format/prettier/md-check/pyright/test]

**Error**:
[Exact error message]

**File**: [file path if applicable]

**Attempted Fixes**:

1. [What you tried first]
2. [What you tried second]
3. [What you tried third]

**Next Steps**:
[Suggest what needs to be done manually]
```

## Success Reporting Format

When all checks pass, format the output with **blank lines** between each check for proper CLI rendering:

```markdown
## Finalization Status: SUCCESS

All CI checks passed after N iteration(s):

✅ **Lint (ruff check)**: PASSED

✅ **Format (ruff format --check)**: PASSED

✅ **Prettier**: PASSED

✅ **AGENTS.md Standard (md-check)**: PASSED

✅ **Pyright**: PASSED

✅ **Tests**: PASSED

✅ **Sync-Kit (dot-agent check)**: PASSED

The code is ready for commit/PR.
```

**IMPORTANT**: Each check line MUST be separated by a blank line in the markdown output to render properly in the CLI.

## Important Guidelines

1. **Be systematic**: Fix one type of error at a time
2. **Run full CI**: Always run full `make all-ci`, not individual checks
3. **Use runner agent**: Always use the Task tool with runner agent for ALL make commands
4. **Run from repo root**: Always ensure make commands execute from repository root
5. **Track progress**: Use TodoWrite for every iteration
6. **Don't guess**: Read files before making changes
7. **Follow standards**: Adhere to AGENTS.md coding standards
8. **Fail gracefully**: Report clearly when stuck
9. **Be efficient**: Use targeted fixes (don't reformat everything for one lint error)

## Example Flow

```
Iteration 1:
- Use Task tool with runner agent to run make all-ci from repo root
- Found: 5 lint errors, 2 files need formatting
- Fix: Use Task tool with runner agent to run make fix, then make format from repo root
- Result: 3 lint errors remain

Iteration 2:
- Use Task tool with runner agent to run make all-ci from repo root
- Found: 3 lint errors (imports)
- Fix: Edit files to fix import issues
- Result: All lint/format pass, 2 type errors

Iteration 3:
- Use Task tool with runner agent to run make all-ci from repo root
- Found: 2 pyright errors in switch.py:45 and switch.py:67
- Fix: Add type annotations
- Result: All checks pass

SUCCESS
```

## Begin Now

Start by using the Task tool with the runner agent to run `make all-ci` from the repository root and begin the iterative fix process. Track your progress with TodoWrite and report your final status clearly.

**Remember**:

- NEVER run make commands directly via Bash
- Always use the Task tool with subagent_type: runner
- Always ensure make commands execute from the repository root directory
