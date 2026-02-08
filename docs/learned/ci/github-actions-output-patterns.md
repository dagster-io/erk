---
title: GitHub Actions Output Patterns
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

## Why Heredoc for Multi-Line Content

The heredoc pattern exists because GitHub Actions reads `$GITHUB_OUTPUT` as a file with key-value pairs. Multi-line values need delimiters to avoid ambiguity:

```yaml
echo "key<<EOF" >> "$GITHUB_OUTPUT"
echo "$MULTI_LINE_VALUE" >> "$GITHUB_OUTPUT"
echo "EOF" >> "$GITHUB_OUTPUT"
```

**Why this matters**: Simple `echo "key=$VALUE" >> $GITHUB_OUTPUT` only captures the first line. GitHub Actions parses the file line-by-line, so undelimited multi-line content becomes multiple key-value pairs (incorrectly).

The `<<EOF` syntax tells GitHub Actions "everything until EOF is the value for this key." This is file format syntax, not shell heredoc syntax - the resemblance is coincidental.

## All Outputs Are Strings

GitHub Actions has no type system. Everything is a string, including booleans and numbers:

```yaml
# Correct
if: steps.check.outputs.skip != 'true'

# Wrong - always evaluates to true because non-empty string is truthy
if: steps.check.outputs.skip == true
```

**Why this trips people up**: Most CI systems have typed outputs. GitHub Actions doesn't. Use string comparisons always.

## The ARG_MAX Boundary

When should you use heredoc vs simple echo? The decision point is whether content might contain newlines, not size:

- **Single-line values** (git SHAs, branch names, booleans): Simple echo works
- **Multi-line values** (rebase output, JSON, logs): Heredoc required

This is orthogonal to the ARG_MAX issue in `gh pr comment`. GitHub Actions writes to `$GITHUB_OUTPUT` via redirection (`>>`), which bypasses ARG_MAX because it's file I/O, not command-line arguments.

## JSON Outputs for Structured Data

For passing structured data between jobs, output JSON and parse with `fromJson()` in the consumer:

<!-- Source: .github/workflows/ci.yml, check-submission job output -->

See the `check-submission` job in `.github/workflows/ci.yml` - it outputs `skip` as a string that downstream jobs consume via `needs.check-submission.outputs.skip == 'false'`.

**Why use JSON**: When multiple related values need to pass together (e.g., session ID + file path), a single JSON output is clearer than multiple flat outputs. The `fromJson()` function converts the string back to a structured object in the consuming job.

## Real Implementation Examples

<!-- Source: .github/workflows/plan-implement.yml -->
<!-- Source: .github/workflows/pr-fix-conflicts.yml -->

See `.github/workflows/plan-implement.yml` for canonical patterns:

- **Line 78**: Simple single-line output for trunk branch detection
- **Line 156**: Single-line output for git SHA capture
- **Line 169**: Exit code capture with conditional boolean output
- **Line 188**: Session info capture using `eval` with environment variable export pattern

See `.github/workflows/pr-fix-conflicts.yml` for heredoc pattern:

- **Lines 112-114**: Multi-line rebase output capture using heredoc syntax

These examples show the decision boundary: git SHAs and booleans use simple echo; command output that may span multiple lines uses heredoc.

## Exit Code Capture Pattern

The `set +e` / `set -e` sandwich is GitHub Actions' idiom for capturing exit codes without failing the step:

```yaml
set +e
some_command
EXIT_CODE=$?
set -e
echo "exit_code=$EXIT_CODE" >> $GITHUB_OUTPUT
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
