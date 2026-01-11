---
title: erk-statusline Architecture
read_when:
  - "modifying the Claude Code status line"
  - "adding new statusline entries or components"
  - "understanding statusline performance or caching"
  - "debugging statusline display issues"
---

# erk-statusline Architecture

A comprehensive guide to the erk-statusline package architecture for adding and modifying status line components.

## Overview

**erk-statusline** is a standalone Python package that generates Claude Code's status line. It operates as a CLI tool invoked by Claude Code on each prompt, receiving workspace/session data via JSON stdin and outputting ANSI-colored text to stdout.

**Entry Point:** `erk_statusline.statusline:main`

**Key Design Principles:**

- Gateway pattern for testability (dependency injection)
- Parallel GitHub API fetching for performance
- File-based caching to reduce API calls
- Never crash (graceful degradation to defaults)
- Immutable token-based rendering for terminal output

## Package Structure

```
packages/erk-statusline/src/erk_statusline/
├── statusline.py        # Main logic, data fetching, display building
├── colored_tokens.py    # Immutable Token/TokenSeq for ANSI rendering
├── context.py           # StatuslineContext (gateway DI container)
├── __main__.py          # CLI entry point
└── __init__.py
```

## Core Components

### 1. Token/TokenSeq Pattern (colored_tokens.py)

Provides an immutable, declarative API for building terminal-formatted strings with ANSI color codes.

**Token:** Atomic piece of text with optional color

```python
Token("main", color=Color.CYAN)
# Renders: "\033[96mmain\033[90m" (cyan text, then restore to gray)
```

**TokenSeq:** Immutable sequence of Tokens and/or other TokenSeqs

```python
TokenSeq((Token("(git:"), Token("main", color=Color.CYAN), Token(")")))
# Renders: "(git:\033[96mmain\033[90m)"
```

**Key Characteristics:**

- Frozen dataclasses (immutable)
- Operations return new instances (`.add()`, `.extend()`)
- Automatic color restoration to GRAY after colored tokens
- Composition via tuple unpacking for conditional inclusion

**Helper Functions:**

- `context_label(sources, value, color)` - Creates labels like `(git:main)` or `({wt, br}:name)`
- `metadata_label(key, value)` - Creates labels like `[st:👀💥]`
- `hyperlink_token(url, text, color)` - Creates clickable hyperlinks using OSC 8 escape sequences

**Color Enum:**

- `CYAN` - Git repo names
- `YELLOW` - Worktree names
- `RED` - Branch names
- `GRAY` - Default/reset color
- `BLUE` - Hyperlinks

### 2. Gateway Pattern (StatuslineContext)

**StatuslineContext** is a frozen dataclass providing dependency injection for all external operations:

```python
@dataclass(frozen=True)
class StatuslineContext:
    cwd: Path
    git: Git
    graphite: Graphite
    github: GitHub
    branch_manager: BranchManager
```

**Purpose:** Enables testability by allowing fake gateways in tests while using real implementations in production.

**Factory Function:**

- `create_context(cwd: str)` - Creates context with real gateway implementations
- Mirrors the pattern in `src/erk/core/context.py`
- Extracts `RepoInfo` upfront for GitHub operations

**Gateway Resolution:**

- `resolve_graphite(installation, gt_installed)` - Determines Graphite implementation based on config and `gt` availability
- Returns `GraphiteDisabled` if not configured or not installed
- Testable via `gt_installed` parameter override

### 3. Parallel GitHub API Fetching

**Performance Strategy:** Fetch PR details and check runs concurrently to minimize latency.

**Implementation:** `fetch_github_data_via_gateway()` in statusline.py

```python
with ThreadPoolExecutor(max_workers=2) as executor:
    pr_future = executor.submit(lambda: _fetch_pr_details(...))
    checks_future = executor.submit(lambda: _fetch_check_runs(...))

    pr_details = pr_future.result(timeout=2)
    check_contexts = checks_future.result(timeout=2)
```

**Timeout Strategy:**

- Per-call timeout: 1.5s for each GitHub API request
- Executor timeout: 2s total for parallel execution
- On timeout: Fall back to defaults (never crash)

**API Endpoints:**

- PR details: `gh api repos/{owner}/{repo}/pulls/{pr_number}` (REST)
- Check runs: `gh api repos/{owner}/{repo}/commits/{ref}/check-runs` (REST)

**Critical Detail:** Check runs use **branch name** (not local SHA) as the ref parameter. This resolves to GitHub's HEAD for that branch, avoiding issues when the local branch differs from remote (e.g., after Graphite squash).

**Error Handling:**

- All subprocess calls wrapped in try/except
- Returns empty defaults on failure (empty string, empty list, "UNKNOWN")
- Logs errors to session-specific file (never stderr)

### 4. Caching Strategy

**Purpose:** Reduce GitHub API calls by caching PR number and head SHA for recently-seen branches.

**Cache Location:** `/tmp/erk-statusline-cache/`

**Cache Key:** SHA256 hash (first 16 chars) of branch name

- Format: `{owner}-{repo}-{branch_hash}.json`
- Example: `dagster-io-erk-abc123def456.json`

**Cache Content:**

```json
{
  "pr_number": 123,
  "head_sha": "abc123..."
}
```

**TTL:** 30 seconds (configured via `CACHE_TTL_SECONDS`)

**Cache Operations:**

- `_get_cache_path(owner, repo, branch)` - Generate cache file path
- `_get_cached_pr_info(owner, repo, branch)` - Read cache if valid
- `_set_cached_pr_info(owner, repo, branch, pr_number, head_sha)` - Write cache

**Cache Validation:**

- Checks file modification time against TTL
- Returns `None` if expired or invalid
- Gracefully handles JSON parse errors

**Note:** Current implementation has cache functions but they are **not actively used** in the data flow. PR info comes from BranchManager (Graphite cache or GitHub API).

### 5. Data Flow

**Input:** JSON on stdin from Claude Code

```json
{
  "workspace": { "current_dir": "/path/to/repo" },
  "model": { "display_name": "Sonnet", "id": "..." },
  "session_id": "abc-123"
}
```

**Processing Pipeline:**

1. **Extract workspace info** - Parse JSON stdin for `cwd`, `model`, `session_id`
2. **Create context** - `create_context(cwd)` with real gateways
3. **Fetch git status** - `get_git_status_via_gateway()` → (branch, is_dirty)
4. **Fetch worktree info** - `get_worktree_info_via_gateway()` → (is_linked, name)
5. **Detect plan files** - Check for `.impl/` folder and `*-impl.md` files
6. **Fetch GitHub data** - `fetch_github_data_via_gateway()` in parallel
7. **Build labels** - Assemble TokenSeq components
8. **Render output** - Join tokens with spaces, print to stdout

**Output:** ANSI-colored string to stdout

```
➜ (git:erk) (wt:root) (br:main) (.impl) ✗ | (gh:#123 st:👀 chks:✅) │ (S)
```

### 6. Display Components

**Status Line Structure:**

```
➜ <context-labels> <plan-indicators> <dirty-marker> | <gh-label> │ (<model>)
```

**Context Labels:** `build_context_labels()`

- Hierarchical display: `(git:repo) (wt:worktree) (br:branch) (cwd:path)`
- Smart collapsing: When worktree name == branch name → `({wt, br}:name)`
- Relative path: Only show `cwd` if not at worktree root

**Plan Indicators:**

- `.impl/` folder present → `(.impl)` token
- New plan file found → `(🆕:basename)` token (strips `-impl.md` suffix)

**Dirty Marker:** `✗` if uncommitted changes exist

**GitHub Label:** `build_gh_label()`

- Format: `(gh:#123 plan:#456 st:👀💥 chks:✅)`
- PR number: From BranchManager (Graphite cache or GitHub API)
- Plan number: From `.impl/issue.json` if present
- State emojis:
  - `👀` - published (open, not draft)
  - `🚧` - draft
  - `🎉` - merged
  - `⛔` - closed
- Conflicts: `💥` appended if `mergeable == "CONFLICTING"`
- Checks: `[✅:3 🚫:1 🔄:2]` format (only non-zero counts shown)

**Model Code:** Extracted from model display name/id

- `S¹ᴹ` - Sonnet [1m] model
- `S` - Sonnet
- `O` - Opus
- First letter uppercase - Other models

### 7. Logging

**Purpose:** Debug statusline issues without polluting stderr (which breaks the display).

**Log Location:** `~/.erk/logs/statusline/{session-id}.log`

**Setup:** `_setup_logging(session_id)`

- Creates log directory if needed
- Session-scoped logs for parallel session isolation
- One-time initialization per session

**Log Level:** DEBUG (all operations logged with timing)

**What's Logged:**

- Cache hits/misses with reasons
- GitHub API fetch timing (elapsed time)
- PR/check run data extraction
- Errors and timeouts

## Adding New Statusline Entries

Follow this 6-step pattern when adding new components to the status line.

### Step 1: Fetch Data

Create a function to fetch data from GitHub API (REST or GraphQL).

**Pattern:**

```python
def _fetch_new_data(
    *, owner: str, repo: str, pr_number: int, cwd: str, timeout: float
) -> DataResult:
    """Fetch new data via GitHub API.

    Returns:
        DataResult with parsed data or defaults on error.
    """
    _logger.debug("Fetching new data: %s/%s #%d", owner, repo, pr_number)
    start_time = time.time()
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/..."],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        elapsed = time.time() - start_time
        if result.returncode != 0:
            _logger.debug("Fetch failed in %.2fs", elapsed)
            return DataResult(default_value)

        data = json.loads(result.stdout)
        _logger.debug("Fetch succeeded in %.2fs", elapsed)
        return DataResult(extract_value(data))

    except subprocess.TimeoutExpired:
        _logger.debug("Timeout after %.2fs", time.time() - start_time)
        return DataResult(default_value)
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        _logger.debug("Error: %s", e)
        return DataResult(default_value)
```

**Key Patterns:**

- Use `NamedTuple` for return type (immutable result)
- Always return defaults on error (never crash)
- Log elapsed time and errors
- Use `subprocess.run()` with timeout
- Parse JSON response

### Step 2: Update Data Structure

Add field to `GitHubData` NamedTuple in statusline.py:

```python
class GitHubData(NamedTuple):
    """Complete GitHub data from GraphQL query."""

    owner: str
    repo: str
    pr_number: int
    # ... existing fields ...
    new_field: str  # Add your new field here with type annotation
```

**Note:** Use appropriate default in `fetch_github_data_via_gateway()` when no PR exists.

### Step 3: Extend Parallel Fetch

Add your fetch function to the `ThreadPoolExecutor` in `fetch_github_data_via_gateway()`:

```python
with ThreadPoolExecutor(max_workers=3) as executor:  # Increase max_workers
    pr_future = executor.submit(...)
    checks_future = executor.submit(...)
    new_future = executor.submit(
        lambda: _fetch_new_data(
            owner=owner, repo=repo, pr_number=pr_number, cwd=cwd, timeout=1.5
        )
    )

    # Wait for results
    pr_details = pr_future.result(timeout=2)
    check_contexts = checks_future.result(timeout=2)
    new_data = new_future.result(timeout=2)
```

**Considerations:**

- Adjust `max_workers` to match number of parallel fetches
- Keep per-call timeout at 1.5s
- Keep executor timeout at 2s
- Handle timeout exceptions with defaults

### Step 4: Create Display Function

Build token/string representation for your data:

```python
def build_new_label(new_data: str) -> TokenSeq:
    """Build label for new data.

    Args:
        new_data: Data to display

    Returns:
        TokenSeq for the label like (new:value)
    """
    if not new_data:
        return TokenSeq(())  # Empty sequence if no data

    return TokenSeq((
        Token("(new:"),
        Token(new_data, color=Color.CYAN),
        Token(")"),
    ))
```

**Patterns:**

- Return empty `TokenSeq(())` if no data to display
- Use appropriate color from `Color` enum
- Follow existing label conventions (parentheses, colons)

### Step 5: Integrate into Status Line

Add to `build_gh_label()` or directly in `main()` depending on scope:

**In build_gh_label()** (if PR-specific):

```python
def build_gh_label(
    repo_info: RepoInfo, github_data: GitHubData | None, issue_number: int | None = None
) -> TokenSeq:
    parts = [Token("(gh:")]

    # ... existing logic ...

    # Add new component
    new_value = github_data.new_field if github_data else ""
    if new_value:
        parts.extend([
            Token(" new:"),
            Token(new_value),
        ])

    parts.append(Token(")"))
    return TokenSeq(tuple(parts))
```

**In main()** (if independent component):

```python
statusline = TokenSeq((
    Token("➜ ", color=Color.GRAY),
    # ... existing components ...
    *([build_new_label(new_data)] if new_data else []),
    # ... rest of statusline ...
))
```

**Note:** Use tuple unpacking with conditional to include/exclude components.

### Step 6: Add Tests

Add unit tests for fetch and display functions in `tests/unit/test_statusline.py`:

```python
def test_fetch_new_data_success():
    """Test successful data fetch."""
    # Use fake subprocess or mock gh api call
    result = _fetch_new_data(
        owner="test", repo="repo", pr_number=123, cwd="/tmp", timeout=5.0
    )
    assert result.field == expected_value

def test_build_new_label():
    """Test label rendering."""
    label = build_new_label("test-value")
    rendered = label.render()
    assert "test-value" in rendered
```

**Test Coverage:**

- Success case with valid data
- Error cases (API failure, timeout, invalid JSON)
- Default fallback behavior
- Display rendering with and without data

## Integration with Claude Code

**Invocation:** Claude Code calls `erk-statusline` CLI on each prompt.

**Configuration:** Defined in `.claude/statusline.jsonc`:

```jsonc
{
  "type": "claude-code-cli",
  "command": "erk-statusline",
}
```

**Data Flow:**

1. Claude Code sends JSON to statusline stdin
2. Statusline processes data and fetches GitHub info
3. Statusline outputs ANSI-colored string to stdout
4. Claude Code displays the string in the status bar

**Performance Impact:** Total execution must complete quickly (< 2s) to avoid UI lag. Parallel fetching and caching are critical for responsiveness.

## Related Patterns

### BranchManager Abstraction

**statusline.py** uses `BranchManager` to fetch PR info, which automatically selects between:

- **Graphite cache** (fast, local) - When Graphite is enabled
- **GitHub API** (slower, network) - When Graphite is disabled

**Usage:**

```python
pr_info = ctx.branch_manager.get_pr_for_branch(repo_root, branch)
if pr_info is None:
    # No PR for this branch
    return None
return (pr_info.number, pr_info.state, pr_info.is_draft)
```

**Benefit:** Centralizes PR lookup logic, automatically optimizes based on Graphite availability.

### Not-Found Sentinel Pattern

When checking PR info results, use `isinstance()` check rather than `None` check:

```python
# See: docs/learned/architecture/not-found-sentinel.md
pr_info = ctx.branch_manager.get_pr_for_branch(repo_root, branch)
if pr_info is None:
    # No PR found
    pass
```

**Note:** Current statusline uses `None` for not-found (simpler than sentinel for this use case).

## Common Modifications

### Changing Colors

Edit `Color` enum in colored_tokens.py:

```python
class Color(Enum):
    CYAN = "\033[96m"  # Change ANSI code here
```

### Adjusting Cache TTL

Edit `CACHE_TTL_SECONDS` in statusline.py:

```python
CACHE_TTL_SECONDS = 30  # Increase for longer cache lifetime
```

### Modifying GitHub API Timeout

Edit timeout parameters in `fetch_github_data_via_gateway()`:

```python
_fetch_pr_details(..., timeout=1.5)  # Per-call timeout
pr_details = pr_future.result(timeout=2)  # Total executor timeout
```

### Adding New Context Sources

To add a new context source (like workspace name):

1. Add to `build_context_labels()` parameters
2. Create new `context_label()` call with appropriate sources list
3. Add to statusline assembly in `main()`

## Troubleshooting

### Status Line Not Updating

**Check:** Log file for errors

```bash
tail -f ~/.erk/logs/statusline/{session-id}.log
```

**Common causes:**

- GitHub API rate limiting (check logs for 403 errors)
- Timeout during parallel fetch (check for timeout messages)
- Invalid JSON input from Claude Code (check parse errors)

### Performance Issues

**Check:** Log timing for GitHub API calls

**Optimization strategies:**

- Increase cache TTL to reduce API calls
- Reduce timeout values to fail faster
- Check network latency to api.github.com

### Display Formatting Problems

**Check:** Terminal ANSI support

**Common issues:**

- Color codes not rendering (unsupported terminal)
- OSC 8 hyperlinks not working (terminal doesn't support OSC 8)
- Text alignment issues (emoji width calculation)

## Related Documentation

- [GitHub GraphQL API Patterns](github-graphql.md) - GraphQL usage patterns (though statusline uses REST)
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Adding new gateway methods
