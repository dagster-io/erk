---
description: Debug a GitHub Actions workflow run and recommend fixes
argument-hint: <run-id-or-url>
---

# /debug-run

Debug a failed GitHub Actions workflow run by fetching logs and analyzing the failure.

## Usage

```bash
/debug-run 12345678
/debug-run https://github.com/owner/repo/actions/runs/12345678
```

Accepts either a plain run ID or a full GitHub Actions URL.

## What You'll Get

1. **Failure Summary**: Quick overview of what failed and why
2. **Root Cause Analysis**: Identification of the actual error (not just symptoms)
3. **Fix Recommendations**: For trivial issues, specific code/command fixes. For complex issues, detailed explanation of the problem.

## Complexity Classification

- **Trivial**: Typos, missing dependencies, simple config errors, environment variable issues
- **Non-trivial**: Race conditions, integration failures, complex logic bugs, infrastructure issues

---

## Agent Instructions

You are a CI/CD debugging expert. Your task is to analyze failed GitHub Actions workflow runs and provide actionable recommendations.

### Step 1: Fetch Logs

Call the kit CLI command to fetch the run logs:

```bash
dot-agent run erk fetch-run-logs "$ARGUMENTS"
```

### Step 2: Handle Errors

If the command returns an error, handle appropriately:

**invalid_format**:

```
The run reference must be a run ID (e.g., "12345678") or a GitHub Actions URL
(e.g., "https://github.com/owner/repo/actions/runs/12345678").

Please provide a valid reference and try again.
```

**not_found**:

```
Workflow run not found. This could mean:
- The run ID is incorrect
- The run was deleted
- You don't have access to this repository

Please verify the run ID and your GitHub authentication (gh auth status).
```

**in_progress**:

```
This workflow run is still in progress (status: <status>).
Wait for it to complete before analyzing the failure.

You can check the status at: <run_url from the error if available>
```

**gh_error**:

```
Failed to fetch workflow run information: <message>

Please ensure:
1. GitHub CLI is installed: gh --version
2. You're authenticated: gh auth status
3. You have access to the repository
```

### Step 3: Read and Analyze Logs

If successful, read the log file from the path provided in the response:

```bash
# The response includes "log_file": ".erk/scratch/run-logs-<run_id>.txt"
```

Read this file and analyze the contents.

### Step 4: Identify Failure Patterns

Look for these common failure patterns:

1. **Test Failures**
   - pytest/unittest failures: Look for `FAILED`, `AssertionError`, stack traces
   - Check for flaky tests (non-deterministic failures)

2. **Build Failures**
   - Missing dependencies: `ModuleNotFoundError`, `ImportError`
   - Type errors: `pyright`, `mypy` errors
   - Syntax errors: `SyntaxError`, parse errors

3. **Lint/Format Failures**
   - `ruff check` failures: specific rule violations
   - `prettier` failures: formatting issues

4. **Environment Issues**
   - Missing environment variables
   - Wrong Python version
   - Dependency conflicts

5. **Infrastructure Issues**
   - Network timeouts
   - Service unavailability
   - Rate limiting

### Step 5: Classify Complexity

**Trivial (recommend specific fix)**:

- Typos in code or config
- Missing import statements
- Simple type annotation fixes
- Formatting issues (just run formatter)
- Single test assertion fix
- Environment variable not set

**Non-trivial (explain the problem)**:

- Race conditions or timing issues
- Complex integration failures
- Architectural problems
- Flaky tests requiring redesign
- Security vulnerabilities
- Infrastructure configuration issues

### Step 6: Output Analysis

Format your response as follows:

````markdown
## Workflow Run Analysis

**Run**: <run_id>
**Status**: <conclusion>
**Branch**: <branch>
**Title**: <display_title>

---

## Failure Summary

<Brief 1-2 sentence summary of what failed>

## Root Cause

<Explanation of the actual error - not just symptoms>

## Fix Recommendation

<Based on complexity classification>

### For trivial issues:

Provide specific code changes or commands:

```<language>
# File: path/to/file.py
# Change this:
<old code>

# To this:
<new code>
```
````

Or commands to run:

```bash
<specific commands>
```

### For non-trivial issues:

Explain:

1. What the underlying problem is
2. Why it's happening
3. Possible approaches to fix
4. Any trade-offs to consider

```

## Important Guidelines

1. **Don't guess** - Base analysis only on log content
2. **Find root cause** - Don't just report the error message, explain why it happened
3. **Be specific** - Provide file paths, line numbers, exact changes when possible
4. **Recommend only** - Never automatically apply fixes (per user requirement)
5. **Handle large logs** - If logs are very long, focus on the failure sections first
6. **Check for multiple failures** - Report all failures, not just the first one
7. **Consider context** - The branch name and PR title often hint at what changed
```
