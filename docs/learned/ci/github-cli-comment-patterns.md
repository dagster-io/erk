---
title: "GitHub CLI PR Comment Patterns"
read_when:
  - Posting formatted PR comments from GitHub Actions workflows
  - Debugging escape sequences in `gh pr comment` commands
  - Encountering "Argument list too long" errors when passing content to CLI commands
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
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# GitHub CLI PR Comment Patterns

## The Problem: POSIX vs Bash in GitHub Actions

GitHub Actions runs shell steps in **dash/sh** (POSIX standard), not bash. This creates two critical failure modes when posting formatted PR comments:

### 1. Escape Sequence Loss

**Root cause:** `echo -e` is a bash extension for interpreting backslash escapes (`\n`, `\t`, etc.). In POSIX sh, the `-e` flag may be ignored or behave differently depending on the system's `echo` implementation.

**Symptom:** Literal `\n` characters appear in PR comments instead of newlines, making formatted output unreadable.

**Why this is silent:** No error is reported. The comment posts successfully with malformed formatting, making it a confusing failure mode during PR workflows.

### 2. ARG_MAX Overflow

**Root cause:** Linux kernel limits command-line argument length to approximately 2MB (ARG_MAX). When using `gh pr comment --body "$LARGE_VAR"`, the entire variable value expands into the command's argument list.

**Symptom:** "Argument list too long" errors when CI outputs (rebase logs, test results, build output) exceed the limit.

**Why this matters:** CI outputs are unpredictable in size. A workflow that works for small PRs can fail catastrophically for large ones.

## The Solution: File-Based Input Pattern

<!-- Source: .github/workflows/pr-fix-conflicts.yml, Post status comment to PR step -->

Use `--body-file` with temporary file and `printf "%b"`:

```bash
TEMP_FILE=$(mktemp)
printf "%b" "$CONTENT" > "$TEMP_FILE"
gh pr comment "$PR_NUMBER" --body-file "$TEMP_FILE"
rm "$TEMP_FILE"
```

See the "Post status comment to PR" step in `.github/workflows/pr-fix-conflicts.yml` for production usage.

### Why This Works

**POSIX compatibility:** `printf "%b"` is POSIX standard for interpreting backslash escape sequences. Works identically across all shells (dash, bash, zsh). No platform-specific behavior.

**Bypasses ARG_MAX:** File I/O has no size limit. Content goes directly from file to GitHub API without expanding in command arguments. The kernel limit only applies to `execve()` arguments, not file contents.

**Resource management:** Explicit cleanup with `rm` ensures no temporary file accumulation in CI runners.

## Decision Table: --body vs --body-file

| Content Characteristics           | Use --body-file | Use --body |
| --------------------------------- | --------------- | ---------- |
| Multi-line with escape sequences  | ✅              | ❌         |
| Dynamic content (CI outputs)      | ✅              | ❌         |
| Size unknown or could exceed 1KB  | ✅              | ❌         |
| Short static strings (<100 chars) | ⚠️              | ✅         |
| No formatting needed              | ⚠️              | ✅         |

**Rule:** In CI, **always** use `--body-file` unless content is trivially small and static. The cost of the temp file pattern is negligible, and it prevents silent failures.

## Historical Context

This pattern emerged from debugging PR workflows where rebase outputs with merge conflict details exceeded ARG_MAX. Initial attempts using `echo -e` worked in local bash testing but failed silently in CI with mangled formatting.

The file-based approach was chosen over alternatives:

- **Base64 encoding:** Adds complexity, doesn't solve ARG_MAX
- **Chunking output:** Loses atomic comment updates
- **Truncation:** Loses critical diagnostic information

## Related Patterns

**For workflow-internal data flow:** Use heredoc patterns for `$GITHUB_OUTPUT` (see `github-actions-output-patterns.md`). Heredocs are for step-to-step communication, not external CLI tools.

**For other gh commands:** The same `--body-file` pattern applies to `gh issue create`, `gh issue comment`, and `gh pr create` when posting large or formatted content.

**For ARG_MAX limits generally:** This issue affects any command receiving large arguments. Prefer file-based input (`--file`, `--config`, `--input`) over inline arguments when available.

## Summary

GitHub Actions' POSIX shell environment breaks bash-specific patterns:

1. **Escape sequences:** Use `printf "%b"`, never `echo -e`
2. **Large content:** Use `--body-file` to bypass ARG_MAX limits
3. **Temp files:** Always create with `mktemp` and explicitly `rm` after use

This prevents silent formatting failures and argument overflow errors in CI workflows.
