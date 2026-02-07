---
title: erk-statusline Architecture Guide
read_when:
  - "modifying the Claude Code status line"
  - "adding new status indicators to the statusline"
  - "understanding how statusline fetches GitHub data"
  - "working with Token/TokenSeq patterns"
  - "debugging statusline performance"
---

# erk-statusline Architecture Guide

The erk-statusline package provides a custom status line for Claude Code, displaying git context, PR status, and CI checks.

## Package Structure

The package lives at `packages/erk-statusline/`:

```
packages/erk-statusline/
├── src/erk_statusline/
│   ├── __main__.py      # Entry point (python -m erk_statusline)
│   ├── statusline.py    # Core logic: data fetching, label building, main()
│   ├── colored_tokens.py # Token/TokenSeq pattern for colored output
│   └── context.py       # StatuslineContext with gateway dependency injection
└── tests/
    ├── test_statusline.py
    ├── test_colored_tokens.py
    └── test_context.py
```

Entry point: `erk_statusline.statusline:main`

## Token/TokenSeq Pattern

The statusline uses an immutable token system for building colored terminal output.

### Token

Atomic piece of text with optional ANSI color:

```python
Token("main", color=Color.CYAN)  # Renders: "\033[96mmain\033[90m"
```

When rendered, colored tokens automatically restore to GRAY.

### TokenSeq

Immutable sequence of Tokens and/or other TokenSeqs:

```python
seq = TokenSeq((
    Token("(git:"),
    Token("main", color=Color.CYAN),
    Token(")")
))
print(seq.render())  # "(git:\033[96mmain\033[90m)"
```

### Color Enum

Available colors in `Color`:

- `CYAN` - Git repo names
- `YELLOW` - Worktree names
- `RED` - Branch names
- `GRAY` - Default/reset
- `BLUE` - Hyperlinks

### Helper Functions

- `context_label(sources, value, color)` - Creates `(git:main)` or `({wt, br}:name)`
- `metadata_label(key, value)` - Creates `(st:emoji)` or `(chks:status)`
- `hyperlink_token(url, text, color)` - Creates clickable OSC 8 hyperlinks

## Gateway Pattern (StatuslineContext)

The `StatuslineContext` is a frozen dataclass providing dependency injection for external services:

```python
@dataclass(frozen=True)
class StatuslineContext:
    cwd: Path
    git: Git
    graphite: Graphite
    github: GitHub
    branch_manager: BranchManager
```

Created via `create_context(cwd)` which wires up real implementations.

**Why gateways matter:**

- Enables testability via fake implementations
- Abstracts Graphite vs GitHub API selection through BranchManager
- Isolates subprocess calls from business logic

## Parallel GitHub API Fetching

The statusline fetches PR details and check runs in parallel using `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=2) as executor:
    pr_future = executor.submit(
        lambda: _fetch_pr_details(owner=owner, repo=repo, pr_number=pr_number, ...)
    )
    checks_future = executor.submit(
        lambda: _fetch_check_runs(owner=owner, repo=repo, ref=branch, ...)
    )

    pr_details = pr_future.result(timeout=2)
    check_contexts = checks_future.result(timeout=2)
```

**Timeouts:**

- Per-call timeout: 1.5 seconds
- Executor timeout: 2 seconds
- Error fallback to defaults (never crashes)

**Why parallel:** The statusline runs on every prompt. Serial API calls would add 3+ seconds of latency.

## Caching Strategy

PR info is cached to reduce API calls:

- **Cache location:** `/tmp/erk-statusline-cache/`
- **Cache key:** SHA256 hash of `{owner}-{repo}-{branch}`
- **TTL:** 30 seconds
- **Stores:** `pr_number`, `head_sha`

The cache reduces GitHub API rate limit pressure for rapidly changing status lines.

## Data Flow

1. **Input:** JSON from stdin with workspace/model info from Claude Code
2. **Git status:** Branch name, dirty status via Git gateway
3. **Worktree detection:** Root vs linked worktree via `git.list_worktrees()`
4. **PR lookup:** BranchManager checks Graphite cache or GitHub API
5. **Parallel fetch:** PR mergeable status + check runs (GitHub REST API)
6. **Token building:** Build TokenSeq from components
7. **Output:** ANSI-colored string to stdout

## Adding New Statusline Entries

Follow this 6-step pattern when adding new information to the statusline:

### Step 1: Fetch Data

Create a function to fetch from GitHub API. Use REST API when possible (GraphQL has separate rate limits):

```python
def _fetch_review_threads(
    *, owner: str, repo: str, pr_number: int, cwd: str, timeout: float
) -> ReviewThreadsResult:
    """Fetch review thread resolution status."""
    # Use gh api for REST, or gh api graphql for GraphQL
    result = subprocess.run(
        ["gh", "api", f"repos/{owner}/{repo}/pulls/{pr_number}/reviews"],
        cwd=cwd, capture_output=True, text=True, timeout=timeout,
    )
    # Parse and return
```

### Step 2: Update Data Structure

Add field to `GitHubData` NamedTuple:

```python
class GitHubData(NamedTuple):
    # ... existing fields ...
    review_thread_count: int  # Total review threads
    resolved_thread_count: int  # Resolved threads
```

### Step 3: Extend Parallel Fetch

Add to `ThreadPoolExecutor` in `fetch_github_data_via_gateway()`:

```python
with ThreadPoolExecutor(max_workers=3) as executor:  # Increase from 2
    pr_future = executor.submit(...)
    checks_future = executor.submit(...)
    threads_future = executor.submit(
        lambda: _fetch_review_threads(owner=owner, repo=repo, ...)
    )
```

### Step 4: Create Display Function

Build a function that returns Token or string representation:

```python
def get_threads_status(github_data: GitHubData | None) -> str:
    """Format thread resolution status."""
    if not github_data or github_data.review_thread_count == 0:
        return ""

    resolved = github_data.resolved_thread_count
    total = github_data.review_thread_count

    if resolved == total:
        return "cmts:check"  # All resolved
    return f"cmts:{resolved}/{total}"
```

### Step 5: Integrate into Label

Add to `build_gh_label()` or main statusline:

```python
# In build_gh_label()
threads_status = get_threads_status(github_data)
if threads_status:
    parts.extend([
        Token(" "),
        Token(threads_status),
    ])
```

### Step 6: Add Tests

Add unit tests for both fetch and display functions in `tests/test_statusline.py`.

## Logging

Logs go to `~/.erk/logs/statusline/{session-id}.log` for debugging:

```python
_logger.debug("Fetching GitHub data for branch=%s", branch)
```

Logs are file-based to avoid polluting stderr (which would break the status line).

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
