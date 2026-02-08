---
title: GitHub CLI Limits
last_audited: "2026-02-07 20:50 PT"
audit_result: clean
read_when:
  - "using gh pr diff in production code"
  - "working with large pull requests (300+ files)"
  - "encountering HTTP 406 errors from gh CLI"
  - "implementing PR file discovery"
  - "working with GitHub codespaces in code"
  - "implementing codespace operations"
tripwires:
  - action: "using gh pr diff --name-only in production code"
    warning: "For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead."
  - action: "using gh codespace start"
    warning: "gh codespace start does not exist. Use REST API POST /user/codespaces/{name}/start via gh api instead."
---

# GitHub CLI Limits

The GitHub CLI wraps both REST and GraphQL APIs with command-line convenience. This abstraction occasionally conceals critical limitations — size thresholds, missing commands, and API quotas — that only surface under production load.

## Why gh pr diff Fails on Large PRs

`gh pr diff` fetches the entire diff in a single unbounded API request. GitHub's API rejects oversized diffs with HTTP 406, typically around 300+ changed files. The gh CLI provides no pagination option for this command.

This is a **test-vs-production tripwire**: small PRs work perfectly in development, large refactors fail silently in CI or production tooling.

### Decision: When to Use REST API Over gh pr Commands

| Use Case                     | Method                                                    | Reason                                            |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------------- |
| Get changed files (any size) | `gh api repos/{owner}/{repo}/pulls/{pr}/files --paginate` | REST API supports pagination, gh pr diff does not |
| Small PR diff (<100 files)   | `gh pr diff {pr}`                                         | Simpler command for common case                   |
| Large PR diff (300+ files)   | `gh api` with REST                                        | gh pr diff will HTTP 406                          |

The REST API approach is **always safe** — it works for all PR sizes. The gh pr diff convenience command is **conditionally safe** — fast path for small PRs, broken path for large ones.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.get_pr_changed_files -->
<!-- Source: src/erk/cli/commands/exec/scripts/discover_reviews.py, discover_reviews command -->

See `RealGitHub.get_pr_changed_files()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the production implementation using REST API with `--paginate`. The `discover_reviews` command in `src/erk/cli/commands/exec/scripts/discover_reviews.py` consumes this gateway method, demonstrating the pattern in a production exec script.

**Decision context**: PR #6119 fixed this after `erk exec discover-reviews` failed on large PRs. The original implementation worked in all manual testing (small PRs) but broke on the first large refactor.

## gh codespace start Does Not Exist

The GitHub CLI documentation implies `gh codespace start` exists. It does not. The command fails with "unknown command 'start'".

This is a **documentation-vs-implementation gap**: reasonable to expect based on `gh codespace stop`, but never implemented.

### Workaround: Use REST API Directly

```bash
gh api --method POST "user/codespaces/${CODESPACE_NAME}/start"
```

The operation is **asynchronous** — the API call returns immediately while the codespace continues starting. Callers must poll codespace state or implement retry logic with timeouts.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/real.py, RealCodespace.start -->

See `RealCodespace.start()` in `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` for the production implementation using `gh api --method POST`.

## GH-API-AUDIT Convention

The codebase uses `GH-API-AUDIT` annotations to track gh CLI commands that could be replaced with direct REST or GraphQL API calls:

```python
# GH-API-AUDIT: [REST/GraphQL] - [operation description]
subprocess.run(["gh", "pr", "view", pr_number])
```

**Format**:

- `REST` — operation has a known REST API endpoint
- `GraphQL` — operation may be better served by GraphQL
- Operation description — brief explanation

**Purpose**: Identifies 66+ locations in the gateway code where we're using gh CLI abstractions that hide quota usage, lack features (like pagination), or impose size limits. The audit trail enables systematic migration when we encounter gh CLI limitations.

## Related Limitations

### GitHub Machines Endpoint HTTP 500 Bug

The `/repos/{owner}/{repo}/codespaces/machines` endpoint returns HTTP 500 for certain repositories (not all repos). The workaround uses `POST /user/codespaces` with `repository_id` instead of fetching available machine types first.

**Default machine type**: `premiumLinux` (hardcoded because the machines endpoint is unreliable)

**Full diagnostic methodology**: See [GitHub API Diagnostics](github-api-diagnostics.md) for repository-specific diagnostic patterns.

<!-- Source: src/erk/cli/commands/codespace/setup_cmd.py, default machine type selection -->

## Cross-References

- [GitHub API Diagnostics](github-api-diagnostics.md) — Repository-specific diagnostic methodology for GitHub API failures
- [Universal Tripwires](../universal-tripwires.md) — Lists the gh pr diff tripwire for pre-coding awareness
- [Gateway ABC Implementation](gateway-abc-implementation.md) — How GitHubGateway abstracts CLI limitations with pagination-aware methods
