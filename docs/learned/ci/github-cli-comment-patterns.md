---
title: "GitHub CLI PR Comment Patterns"
read_when:
  - Posting formatted PR comments from GitHub Actions workflows
  - Debugging escape sequences in `gh pr comment` commands
  - Encountering "Argument list too long" errors
  - Writing GitHub Actions steps that use `gh pr` commands with multi-line content
sources:
  - "[Impl e5da072c]"
  - "[Impl f871bb54]"
  - "[Impl 5d99bc36]"
  - "[PR #6388]"
tripwires:
  - action: 'Writing GitHub Actions workflow steps that pass large content to `gh` CLI commands (e.g., `gh pr comment --body "$VAR"`)'
    warning: "Use `--body-file` or other file-based input to avoid Linux ARG_MAX limit (~2MB on command-line arguments). Large CI outputs like rebase logs can exceed this limit."
  - action: "Using escape sequences like `\\n` in GitHub Actions workflows"
    warning: 'Use `printf "%b"` instead of `echo -e` for reliable escape sequence handling. GitHub Actions uses dash/sh (POSIX standard), not bash, so `echo -e` behavior differs from local development.'
  - action: "GitHub Actions workflow needs to perform operations like gist creation, or session uploads fail in CI"
    warning: "GitHub Actions GITHUB_TOKEN has restricted scope by default. Check token capabilities or use personal access token (PAT) for elevated permissions like gist creation."
---

# GitHub CLI PR Comment Patterns

## Overview

When posting formatted PR comments from GitHub Actions workflows using `gh pr comment`, two common failure modes occur:

1. **Escape sequences appear literally** (`\n` instead of newlines)
2. **"Argument list too long" errors** when content exceeds ~2MB

This document covers the correct pattern for posting multi-line formatted content via `gh pr comment` in CI environments.

## The Problem

### Inline --body with Command Substitution

The intuitive approach fails in CI:

```yaml
gh pr comment "$PR_NUMBER" --body "$(echo -e "$BODY")"
```

**Why this fails:**

1. **Escape sequence loss**: GitHub Actions uses dash/sh (POSIX standard), not bash. The `echo -e` flag for interpreting escape sequences is a bash extension that may be ignored or behave unexpectedly in dash. Result: literal `\n` characters appear in PR comments.

2. **ARG_MAX overflow**: Linux kernel limits command-line argument length to ~2MB (ARG_MAX). Large CI outputs (rebase logs, test results) passed as `--body "$VAR"` can exceed this limit, causing "Argument list too long" errors.

3. **Silent degradation**: When escape sequences fail, PR comments render with malformed formatting but no error is reported - a confusing failure mode.

## The Solution

Use `--body-file` with temporary file pattern:

```yaml
TEMP_FILE=$(mktemp)
printf "%b\n" "$BODY" > "$TEMP_FILE"
gh pr comment "$PR_NUMBER" --body-file "$TEMP_FILE"
rm "$TEMP_FILE"
```

### Why This Works

1. **Reliable escape sequence handling**: `printf "%b"` is POSIX standard for interpreting backslash escape sequences (`\n`, `\t`, etc.). Works consistently across all shells.

2. **Bypasses ARG_MAX**: File I/O has no size limit. The content goes directly from file to GitHub API, never expanding in command-line arguments.

3. **Proper cleanup**: Temporary file is explicitly removed after use.

## Real-World Example

From `.github/workflows/pr-fix-conflicts.yml`:

**Before (broken):**

```yaml
BODY="## Conflict Resolution Failed\n\nRebase output:\n\`\`\`\n$REBASE_OUTPUT\n\`\`\`"
gh pr comment "$PR_NUMBER" --body "$(echo -e "$BODY")"
```

**Problems:**

- Literal `\n` in PR comments
- Fails when `$REBASE_OUTPUT` exceeds ~2MB

**After (fixed):**

```yaml
BODY="## Conflict Resolution Failed\n\nRebase output:\n\`\`\`\n$REBASE_OUTPUT\n\`\`\`"
TEMP_FILE=$(mktemp)
printf "%b\n" "$BODY" > "$TEMP_FILE"
gh pr comment "$PR_NUMBER" --body-file "$TEMP_FILE"
rm "$TEMP_FILE"
```

**Benefits:**

- Escape sequences interpreted correctly
- No size limits
- Clean resource management

## When to Use Each Pattern

### Use --body-file (preferred in CI):

- Multi-line content with escape sequences
- Dynamic content of unknown size
- Any content that could potentially be large (>1KB)
- GitHub Actions workflows posting CI outputs

### Use --body (acceptable only for):

- Short, static strings with no formatting
- Content guaranteed to be under 100 characters
- No escape sequences needed

**Rule of thumb**: In CI, always use `--body-file` unless the content is trivially small and static.

## Related Patterns

- **For `$GITHUB_OUTPUT`**: Use heredoc patterns (see `github-actions-output-patterns.md`). Heredoc is for workflow step-to-step data flow, not for external CLI tools.
- **For ARG_MAX limits**: See tripwire in `ci/tripwires.md`
- **For POSIX portability**: See "Printf vs Echo -e" tripwire in `ci/tripwires.md`

## Summary

In GitHub Actions workflows posting PR comments:

1. Create temp file: `TEMP_FILE=$(mktemp)`
2. Write with `printf "%b"`: `printf "%b\n" "$CONTENT" > "$TEMP_FILE"`
3. Use `--body-file`: `gh pr comment "$PR" --body-file "$TEMP_FILE"`
4. Cleanup: `rm "$TEMP_FILE"`

This pattern avoids escape sequence loss, bypasses ARG_MAX limits, and works consistently across all CI shells.
