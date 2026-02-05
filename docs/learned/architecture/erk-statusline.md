---
title: erk-statusline Architecture Guide
read_when:
  - "modifying the Claude Code status line"
  - "adding new status indicators to the statusline"
  - "understanding how statusline fetches GitHub data"
  - "working with Token/TokenSeq patterns"
  - "debugging statusline performance"
last_audited: "2026-02-05 14:19 PT"
audit_result: edited
---

# erk-statusline Architecture Guide

The erk-statusline package provides a custom status line for Claude Code, displaying git context, PR status, and CI checks.

## Package Structure

The package lives at `packages/erk-statusline/`. Source modules are in `src/erk_statusline/` and tests in `tests/`. Entry point: `erk_statusline.statusline:main`.

Key modules:

- `statusline.py` -- Core logic: data fetching, label building, `main()`
- `colored_tokens.py` -- Token/TokenSeq pattern for colored output (see module docstring for full API)
- `context.py` -- `StatuslineContext` with gateway dependency injection

## Token/TokenSeq Pattern

The statusline uses an immutable token system for building colored terminal output. See the module docstring in `colored_tokens.py` for full API documentation and usage examples.

Key concepts:

- **Token** -- Atomic piece of text with optional ANSI color. Colored tokens automatically restore to GRAY after rendering.
- **TokenSeq** -- Immutable sequence of Tokens and/or other TokenSeqs. Operations like `add()` and `extend()` return new instances.
- **Color enum** -- `CYAN` (git repo names), `YELLOW` (worktree names), `RED` (branch names), `GRAY` (default/reset), `BLUE` (hyperlinks)
- **Helper functions** -- `context_label()`, `metadata_label()`, `hyperlink_token()` for common label patterns

## Gateway Pattern (StatuslineContext)

`StatuslineContext` is a frozen dataclass providing dependency injection for external services. See `context.py` for the class definition and `create_context()` factory.

Fields: `cwd`, `git`, `graphite`, `github`, `branch_manager`.

**Why gateways matter:**

- Enables testability via fake implementations
- Abstracts Graphite vs GitHub API selection through BranchManager
- Isolates subprocess calls from business logic

## Parallel GitHub API Fetching

The statusline fetches three things in parallel using `ThreadPoolExecutor(max_workers=3)` in `fetch_github_data_via_gateway()`:

1. **PR details** (mergeable status, head SHA) via `_fetch_pr_details()`
2. **Check runs** via `_fetch_check_runs()`
3. **Review thread counts** via `_fetch_review_thread_counts()`

**Timeouts:**

- Per-call timeout: `1.5` seconds
- Executor timeout: `2` seconds
- Error fallback to defaults (never crashes)

**Why parallel:** The statusline runs on every prompt. Serial API calls would add 3+ seconds of latency.

## Caching Strategy

PR info is cached to reduce API calls:

- **Cache location:** `/tmp/erk-statusline-cache/`
- **Cache key:** Filename is `{owner}-{repo}-{hash}.json` where hash is SHA256 of branch name (first 16 hex chars)
- **TTL:** `30` seconds
- **Stores:** `pr_number`, `head_sha`

The cache reduces GitHub API rate limit pressure for rapidly changing status lines.

## Data Flow

1. **Input:** JSON from stdin with workspace/model info from Claude Code
2. **Git status:** Branch name, dirty status via Git gateway
3. **Worktree detection:** Root vs linked worktree via `ctx.git.worktree.list_worktrees()`
4. **PR lookup:** BranchManager checks Graphite cache or GitHub API
5. **Parallel fetch:** PR mergeable status + check runs + review thread counts (3 concurrent API calls)
6. **Token building:** Build TokenSeq from components
7. **Output:** ANSI-colored string to stdout

## Adding New Statusline Entries

Follow this 6-step pattern when adding new information to the statusline. Use `_fetch_review_thread_counts()` in `statusline.py` as a concrete reference implementation -- it was the most recently added fetch.

### Step 1: Fetch Data

Create a `_fetch_*` function in `statusline.py` following the pattern of existing fetch functions. Use REST API when possible (GraphQL has separate rate limits). Each fetch function should accept `owner`, `repo`, `cwd`, `timeout` keyword arguments and return a typed result.

### Step 2: Update Data Structure

Add a field to the `GitHubData` NamedTuple in `statusline.py`. Current fields include `review_thread_counts: tuple[int, int]` as a reference for how to structure new data.

### Step 3: Extend Parallel Fetch

Add a new `executor.submit()` call inside the `ThreadPoolExecutor` block in `fetch_github_data_via_gateway()`. Increase `max_workers` if needed. Wire the result into the `GitHubData` return value.

### Step 4: Create Display Function

Build a function that converts the new `GitHubData` field into a display string or Token. See `build_comment_count_label()` for the pattern.

### Step 5: Integrate into Label

Add the new display output into `build_gh_label()` following the existing pattern of conditionally extending `parts`.

### Step 6: Add Tests

Add unit tests for both fetch and display functions in `tests/test_statusline.py`.

## Logging

Logs go to `~/.erk/logs/statusline/{session-id}.log`. They are file-based to avoid polluting stderr, which would break the status line display.

## Key Design Principles

1. **Never crash:** Errors fallback to defaults, showing partial info
2. **Fast execution:** Parallel fetches, caching, strict timeouts
3. **Immutable data:** Frozen dataclasses and NamedTuples throughout
4. **Gateway abstraction:** All external calls through injectable gateways
5. **Composable output:** Token/TokenSeq enables clean conditional rendering

## Related Topics

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Adding gateway methods
- [GitHub API Rate Limits](github-api-rate-limits.md) - REST vs GraphQL considerations
- [GitHub GraphQL](github-graphql.md) - GraphQL patterns for data not in REST
