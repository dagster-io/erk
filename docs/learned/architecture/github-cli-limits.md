---
title: GitHub CLI Limits
last_audited: "2026-02-16 14:20 PT"
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
    pattern: "gh\\s+pr\\s+diff\\s+--name-only"
  - action: "using gh codespace start"
    warning: "gh codespace start does not exist. Use REST API POST /user/codespaces/{name}/start via gh api instead."
    pattern: "gh\\s+codespace\\s+start"
  - action: "using -f body=@file with gh api"
    warning: "-f body=@file sends the literal string '@file', not file contents. Use --input with a JSON payload instead."
    pattern: "-f\\s+body=@"
---

# GitHub CLI Limits

The GitHub CLI wraps both REST and GraphQL APIs with command-line convenience. This abstraction occasionally conceals critical limitations — size thresholds, missing commands, and API quotas — that only surface under production load.

## Why gh pr diff Fails on Large PRs

`gh pr diff` fetches the entire diff in a single unbounded API request. GitHub's API rejects oversized diffs with HTTP 406, typically around 300+ changed files. The gh CLI provides no pagination option for this command.

This is a **test-vs-production tripwire**: small PRs work perfectly in development, large refactors fail silently in CI or production tooling.

### Failure Example

```bash
gh pr diff 123 --name-only
# Error: HTTP 406: Not Acceptable (https://api.github.com/...)
```

### The Solution: REST API with Pagination

Use the GitHub REST API `/repos/{owner}/{repo}/pulls/{pr}/files` endpoint, which supports pagination:

```bash
gh api \
  --paginate \
  --jq '.[].filename' \
  "repos/{owner}/{repo}/pulls/${PR_NUMBER}/files"
```

### gh pr diff vs gh api Comparison

| Method                             | Pagination         | Size Limit | Failure Mode   |
| ---------------------------------- | ------------------ | ---------- | -------------- |
| `gh pr diff --name-only`           | No                 | ~300 files | HTTP 406 error |
| `gh api repos/.../pulls/.../files` | Yes (`--paginate`) | No limit   | None           |

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

### Failure Example

```bash
gh codespace start mycodespace
# Error: unknown command "start" for "gh codespace"
```

### Workaround: Use REST API Directly

```bash
gh api \
  --method POST \
  "user/codespaces/${CODESPACE_NAME}/start"
```

This returns JSON with the codespace state. The operation is **asynchronous** — the API call returns immediately while the codespace continues starting. Callers must poll codespace state or implement retry logic with timeouts.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace/real.py, RealCodespace.start_codespace -->

See `RealCodespace.start_codespace()` in `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` for the production implementation using `gh api --method POST`.

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

### Examples from Codebase

```python
# GH-API-AUDIT: REST - Get PR number from branch
result = subprocess.run(["gh", "pr", "view", "--json", "number"])

# GH-API-AUDIT: GraphQL - Fetch issue comments
result = subprocess.run(["gh", "issue", "view", issue_number, "--json", "comments"])
```

**Purpose**: Identifies 60+ locations in the gateway code where we're using gh CLI abstractions that hide quota usage, lack features (like pagination), or impose size limits. The audit trail enables systematic migration when we encounter gh CLI limitations.

## Related Limitations

### GitHub Machines Endpoint HTTP 500 Bug

The `/repos/{owner}/{repo}/codespaces/machines` endpoint returns HTTP 500 for certain repositories (not all repos). The workaround uses `POST /user/codespaces` with `repository_id` instead of fetching available machine types first.

**Default machine type**: `premiumLinux` (hardcoded because the machines endpoint is unreliable)

**Full diagnostic methodology**: See [GitHub API Diagnostics](github-api-diagnostics.md) for repository-specific diagnostic patterns.

<!-- Source: src/erk/cli/commands/codespace/setup_cmd.py, default machine type selection -->

## PR Closing Reference Timing

GitHub's `willCloseTarget` behavior is evaluated at PR creation time. Adding a `Closes #N` reference via a post-creation body update does **not** enable auto-close. The closing reference must be present in the initial `create_pr()` call body.

This affects one-shot dispatch and any workflow that creates a PR then later wants to link it to a plan issue. The registration step must ensure the closing reference is in the initial body, not appended afterward.

## `-f` vs `--input` for Request Body Data

The `gh api` command has two mechanisms for sending data, with a critical distinction:

### `-f key=value` — Literal String Fields

`-f body=hello` sends `{"body": "hello"}`. The value is **always a literal string**.

**Common misconception**: `-f body=@file.txt` does **NOT** read file contents. It sends the literal string `@file.txt` as the body value. This has caused data loss in production — an objective comment was corrupted when `-f body=@backup.md` wrote the literal path instead of file contents.

```bash
# WRONG: Sends literal string "@body.md" as the body
gh api repos/owner/repo/issues/comments/123 -X PATCH -f body=@body.md

# The -F flag (uppercase) DOES read files, but only for form-encoded fields:
# -F body=@file reads file contents for multipart form data
```

### `--input <file>` — Full JSON Request Body

`--input payload.json` reads the file and sends its entire contents as the request body.

```bash
# CORRECT: Read file contents as full JSON body
echo '{"body": "new comment text"}' > /tmp/payload.json
gh api repos/owner/repo/issues/comments/123 -X PATCH --input /tmp/payload.json
```

### Decision: When to Use Each

| Use Case                   | Method              | Why                                           |
| -------------------------- | ------------------- | --------------------------------------------- |
| Set a simple string field  | `-f key=value`      | Convenient for inline values                  |
| Send file contents as body | `--input file.json` | Only reliable way to send file data           |
| Update issue/comment body  | `--input` with JSON | Body text can be large, contain special chars |
| Set multiple simple fields | Multiple `-f` flags | Each is a literal key-value pair              |

### Safety Rule: Backup Before Mutating Comments

GitHub does not expose comment edit history. Before updating any comment body:

1. Fetch current body: `gh api repos/{owner}/{repo}/issues/comments/{id} --jq .body > backup.md`
2. Construct JSON payload with new body
3. Update via `--input`

This backup-before-mutate pattern prevents irrecoverable data loss.

## Hardcoded --repo Flag Returns Empty Output

When using `gh api` with a hardcoded `--repo` flag (e.g., `--repo owner/repo`), the flag may silently return empty output if the repo format doesn't match what gh expects. Prefer letting gh infer the repo from the current git remote, or use the full API URL path (`repos/owner/repo/...`) instead.

## Cross-References

- [GitHub API Diagnostics](github-api-diagnostics.md) — Repository-specific diagnostic methodology for GitHub API failures
- [Universal Tripwires](../universal-tripwires.md) — Lists the gh pr diff tripwire for pre-coding awareness
- [Gateway ABC Implementation](gateway-abc-implementation.md) — How GitHubGateway abstracts CLI limitations with pagination-aware methods
- [Codespace Patterns](../cli/codespace-patterns.md) — Codespace setup patterns
