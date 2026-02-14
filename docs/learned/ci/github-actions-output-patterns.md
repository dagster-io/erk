---
title: GitHub Actions Output Patterns
content_type: third_party_reference
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
read_when:
  - "setting outputs in GitHub Actions workflows"
  - "passing data between workflow steps"
  - "handling multi-line content in GITHUB_OUTPUT"
  - "parsing JSON from workflow step outputs"
tripwires:
  - action: "using echo with multi-line content to GITHUB_OUTPUT"
    warning: "Multi-line content requires heredoc syntax with EOF delimiter. Simple echo only works for single-line values."
---

# GitHub Actions Output Patterns

## The Core Problem

GitHub Actions workflows need to pass data **between steps within the runner environment**, not to external APIs. This is a fundamentally different problem than posting comments via `gh pr comment`.

**Critical distinction**: `$GITHUB_OUTPUT` is GitHub Actions' internal step-to-step communication mechanism. Use heredoc patterns here. For external GitHub CLI commands like `gh pr comment`, use `--body-file` with `printf "%b"` instead (see [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md)).

## Basic Output Pattern

For single-line values:

```yaml
- name: Set output
  id: my_step
  run: echo "my_value=hello" >> $GITHUB_OUTPUT

- name: Use output
  run: echo "Got: ${{ steps.my_step.outputs.my_value }}"
```

## Why Heredoc for Multi-Line Content

The heredoc pattern exists because GitHub Actions reads `$GITHUB_OUTPUT` as a file with key-value pairs. Multi-line values need delimiters to avoid ambiguity:

```yaml
- name: Set multi-line output
  id: rebase
  run: |
    REBASE_OUTPUT=$(some_command_with_multiline_output)
    echo "rebase_output<<EOF" >> "$GITHUB_OUTPUT"
    echo "$REBASE_OUTPUT" >> "$GITHUB_OUTPUT"
    echo "EOF" >> "$GITHUB_OUTPUT"

- name: Use multi-line output
  run: |
    echo "Full output:"
    echo "${{ steps.rebase.outputs.rebase_output }}"
```

The heredoc pattern:

1. Write `key<<EOF` to start
2. Write the content (can span multiple lines)
3. Write `EOF` on its own line to end

**Why this matters**: Simple `echo "key=$VALUE" >> $GITHUB_OUTPUT` only captures the first line. GitHub Actions parses the file line-by-line, so undelimited multi-line content becomes multiple key-value pairs (incorrectly).

The `<<EOF` syntax tells GitHub Actions "everything until EOF is the value for this key." This is file format syntax, not shell heredoc syntax - the resemblance is coincidental.

## All Outputs Are Strings

GitHub Actions has no type system. Everything is a string, including booleans and numbers:

```yaml
- name: Check condition
  id: check
  run: |
    if [ -d ".impl" ]; then
      echo "skip=true" >> $GITHUB_OUTPUT
    else
      echo "skip=false" >> $GITHUB_OUTPUT
    fi

- name: Conditional step
  if: steps.check.outputs.skip != 'true'
  run: echo "Running because skip was not true"
```

**Why this trips people up**: Most CI systems have typed outputs. GitHub Actions doesn't. Use string comparisons always (`!= 'true'`, not `== true`).

## The ARG_MAX Boundary

When should you use heredoc vs simple echo? The decision point is whether content might contain newlines, not size:

- **Single-line values** (git SHAs, branch names, booleans): Simple echo works
- **Multi-line values** (rebase output, JSON, logs): Heredoc required

This is orthogonal to the ARG_MAX issue in `gh pr comment`. GitHub Actions writes to `$GITHUB_OUTPUT` via redirection (`>>`), which bypasses ARG_MAX because it's file I/O, not command-line arguments.

## JSON Outputs for Structured Data

For passing structured data between jobs, output JSON and parse with `fromJson()` in the consumer:

### Setting JSON Output

```yaml
- name: Create matrix
  id: matrix
  run: |
    MATRIX='{"include":[{"file":"a.py"},{"file":"b.py"}]}'
    echo "matrix=$MATRIX" >> "$GITHUB_OUTPUT"
```

### Consuming JSON Output with fromJson()

```yaml
jobs:
  matrix-job:
    strategy:
      matrix: ${{ fromJson(steps.matrix.outputs.matrix) }}
```

### Parsing JSON in Shell with jq

```yaml
- name: Parse JSON output
  run: |
    RESULT='${{ steps.previous.outputs.json_data }}'
    VALUE=$(echo "$RESULT" | jq -r '.some_field')
    echo "Extracted: $VALUE"
```

<!-- Source: .github/workflows/ci.yml, check-submission job output -->

See the `check-submission` job in `.github/workflows/ci.yml` - it outputs `skip` as a string that downstream jobs consume via `needs.check-submission.outputs.skip == 'false'`.

**Why use JSON**: When multiple related values need to pass together (e.g., session ID + file path), a single JSON output is clearer than multiple flat outputs. The `fromJson()` function converts the string back to a structured object in the consuming job.

## Common Patterns in Erk Workflows

### Capturing Git State

```yaml
- name: Save pre-implementation HEAD
  id: pre_impl
  run: echo "head=$(git rev-parse HEAD)" >> $GITHUB_OUTPUT

- name: Check for changes
  run: |
    if git diff --quiet ${{ steps.pre_impl.outputs.head }}..HEAD; then
      echo "No changes"
    fi
```

### Detecting PR Numbers

For push events, finding the associated PR requires a GitHub API call. The `discover-pr` step in `.github/workflows/ci.yml` (autofix job) demonstrates the pattern: check `github.event_name` to determine whether the PR number is available directly or needs an API lookup, then set `pr_number` and `has_pr` outputs accordingly.

### Collecting Job Results

Aggregating upstream job results into a single step's outputs enables downstream conditional logic. See the `failures` step in `.github/workflows/ci.yml` (autofix job) for how `needs.<job>.result` values are captured as individual outputs.

### Session Capture

The `eval` + output pattern captures session info from an erk exec command. See the "Capture session ID" step in `.github/workflows/plan-implement.yml` (line 186) for the production pattern: `eval "$OUTPUT"` sets shell variables that are then written to `$GITHUB_OUTPUT`.

## Real Implementation Examples

<!-- Source: .github/workflows/plan-implement.yml -->
<!-- Source: .github/workflows/pr-fix-conflicts.yml -->

See `.github/workflows/plan-implement.yml` for canonical patterns:

- **Trunk branch detection step**: Simple single-line output via echo
- **Git SHA capture step**: Single-line output for commit references
- **Exit code capture step**: Conditional boolean output from process results
- **Session info capture step**: `eval` with environment variable export pattern

See `.github/workflows/pr-fix-conflicts.yml` for heredoc pattern:

- **Rebase output capture step**: Multi-line output using heredoc syntax

These examples show the decision boundary: git SHAs and booleans use simple echo; command output that may span multiple lines uses heredoc.

## Exit Code Capture Pattern

The `set +e` / `set -e` sandwich is GitHub Actions' idiom for capturing exit codes without failing the step:

```yaml
- name: Run with exit code capture
  id: run
  run: |
    set +e  # Don't exit on error
    some_command
    EXIT_CODE=$?
    set -e
    echo "exit_code=$EXIT_CODE" >> $GITHUB_OUTPUT
    if [ $EXIT_CODE -eq 0 ]; then
      echo "success=true" >> $GITHUB_OUTPUT
    else
      echo "success=false" >> $GITHUB_OUTPUT
    fi

- name: Only if succeeded
  if: steps.run.outputs.success == 'true'
  run: echo "Previous step succeeded"
```

**Why this pattern exists**: GitHub Actions fails the step on any non-zero exit code by default. Disabling `set -e` temporarily allows capturing the exit code for conditional logic in downstream steps. This enables "run command, check result, decide what to do" workflows.

Without this pattern, you'd need `continue-on-error: true` on the step, which loses the exit code information.

## Common Anti-Patterns

### Missing Quotes Around $GITHUB_OUTPUT

```yaml
# Wrong - breaks if $GITHUB_OUTPUT has spaces (it won't, but be defensive)
echo "key=value" >> $GITHUB_OUTPUT

# Correct
echo "key=value" >> "$GITHUB_OUTPUT"
```

### Using Heredoc for Single-Line Values

The heredoc pattern has overhead. Don't use it for simple single-line outputs:

```yaml
# Wrong - unnecessary complexity
echo "branch<<EOF" >> "$GITHUB_OUTPUT"
echo "$BRANCH_NAME" >> "$GITHUB_OUTPUT"
echo "EOF" >> "$GITHUB_OUTPUT"

# Correct
echo "branch=$BRANCH_NAME" >> "$GITHUB_OUTPUT"
```

### Newlines in Simple Echo

```yaml
# Wrong - only captures first line
echo "content=$MULTI_LINE_VAR" >> $GITHUB_OUTPUT

# Correct - use heredoc
echo "content<<EOF" >> "$GITHUB_OUTPUT"
echo "$MULTI_LINE_VAR" >> "$GITHUB_OUTPUT"
echo "EOF" >> "$GITHUB_OUTPUT"
```

### Boolean String Comparison

```yaml
# Wrong - comparing to boolean literal
if: steps.check.outputs.skip == true

# Correct - comparing to string
if: steps.check.outputs.skip == 'true'
```

## Boundary with External CLI Commands

This document covers `$GITHUB_OUTPUT` only - internal step-to-step data flow within GitHub Actions runner environment.

For `gh pr comment` and other external GitHub CLI commands that send data to the GitHub API, different rules apply:

- **`$GITHUB_OUTPUT`**: Use heredoc for multi-line values
- **`gh pr comment`**: Use `--body-file` with `printf "%b"` for all formatted content

The heredoc pattern **does not work** for `gh pr comment` because:

1. Heredoc is file format syntax for `$GITHUB_OUTPUT`, not escape sequence interpretation
2. `gh pr comment` requires POSIX-portable escape sequence handling (`printf "%b"`)
3. Large content hits ARG_MAX limits when passed as `--body` arguments

See [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) for the external CLI pattern.

## Related Documentation

- [GitHub CLI PR Comment Patterns](github-cli-comment-patterns.md) - For external CLI tools
- [CI Prompt Patterns](prompt-patterns.md) - Working with prompts in CI
