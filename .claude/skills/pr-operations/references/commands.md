# PR Operations Command Reference

Complete documentation for all `erk exec` commands related to PR thread operations.

## get-pr-review-comments

Fetches unresolved review threads from the current branch's PR.

### Usage

```bash
erk exec get-pr-review-comments          # Unresolved threads only
erk exec get-pr-review-comments --all    # Include resolved threads
```

### Options

| Option  | Description              |
| ------- | ------------------------ |
| `--all` | Include resolved threads |

### JSON Output Format

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_title": "Feature: Add new capability",
  "threads": [
    {
      "id": "PRRT_abc123",
      "path": "src/foo.py",
      "line": 42,
      "is_outdated": false,
      "comments": [
        {
          "author": "reviewer",
          "body": "This should use LBYL pattern instead of try/except",
          "created_at": "2024-01-01T10:00:00Z"
        }
      ]
    }
  ]
}
```

### Field Notes

- `id`: Thread ID starting with `PRRT_` - use this with `resolve-review-thread`
- `path`: File path relative to repository root
- `line`: Line number in the file, or `null` if thread is outdated
- `is_outdated`: `true` if the code has changed since the comment was made
- `comments`: Array of all comments in the thread (chronological order)

### Handling Outdated Threads

When `is_outdated: true`:

1. The `line` field will be `null`
2. Read the file at `path` and search for relevant code mentioned in the comment
3. Check if the issue is already fixed in current code
4. Still resolve the thread via `erk exec resolve-review-thread`

---

## get-pr-discussion-comments

Fetches PR discussion comments (top-level comments, not code review threads).

### Usage

```bash
erk exec get-pr-discussion-comments
```

### JSON Output Format

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_title": "Feature: Add new capability",
  "comments": [
    {
      "id": 12345,
      "author": "reviewer",
      "body": "Please also update the docs",
      "url": "https://github.com/owner/repo/pull/123#issuecomment-12345"
    }
  ]
}
```

### Field Notes

- `id`: Numeric comment ID - use this with `reply-to-discussion-comment`
- `body`: The full comment text
- `url`: Direct link to the comment on GitHub

---

## resolve-review-thread

Replies to a review thread AND marks it as resolved in one operation.

### Usage

```bash
erk exec resolve-review-thread --thread-id "PRRT_abc123" --comment "Fixed in commit abc1234"
```

### Options

| Option        | Required | Description                             |
| ------------- | -------- | --------------------------------------- |
| `--thread-id` | Yes      | Thread ID from `get-pr-review-comments` |
| `--comment`   | Yes      | Reply message to add before resolving   |

### Examples

**Standard resolution:**

```bash
erk exec resolve-review-thread --thread-id "PRRT_abc123" \
  --comment "Resolved via /erk:pr-address at $(date '+%Y-%m-%d %I:%M %p %Z')"
```

**Already-fixed outdated thread:**

```bash
erk exec resolve-review-thread --thread-id "PRRT_abc123" \
  --comment "Already addressed in current code - this outdated thread can be resolved."
```

**False positive from automated reviewer:**

```bash
erk exec resolve-review-thread --thread-id "PRRT_abc123" \
  --comment "False positive: The LBYL check already exists on line 344 where we check .exists() before the operation. No code change needed."
```

### Replying vs Resolving

> **IMPORTANT**: This command does BOTH reply AND resolve.
>
> - Raw `gh api .../replies`: Only adds comment, thread stays OPEN
> - `erk exec resolve-review-thread`: Adds comment AND marks RESOLVED

---

## reply-to-discussion-comment

Posts a reply to a PR discussion comment.

### Usage

```bash
erk exec reply-to-discussion-comment --comment-id 12345 --reply "**Action taken:** Updated the docs."
```

### Options

| Option         | Required | Description                                  |
| -------------- | -------- | -------------------------------------------- |
| `--comment-id` | Yes      | Comment ID from `get-pr-discussion-comments` |
| `--reply`      | Yes      | Reply message                                |

### Writing Substantive Replies

The reply becomes a permanent record in the PR. Make it useful for future readers.

**Bad (too generic):**

```bash
--reply "**Action taken:** Noted for future consideration."
--reply "**Action taken:** Added to backlog."
```

**Good (includes investigation findings):**

```bash
--reply "**Action taken:** Investigated the gateway pattern suggestion. The current implementation uses direct function calls rather than a gateway ABC pattern. This is intentional - artifact operations are file-based and don't require the testability benefits of gateway injection that external APIs need. Filed as backlog consideration for if we add remote artifact fetching."
```

**Good (explains why no code change):**

```bash
--reply "**Action taken:** Reviewed the suggestion to add caching here. After checking the call sites, this function is only called once per CLI invocation (in main.py:45), so caching wouldn't provide measurable benefit. The perceived slowness is actually from the subprocess call inside, not repeated invocations."
```

---

## post-pr-inline-comment

Posts a new inline comment on a specific line of code in a PR.

### Usage

```bash
erk exec post-pr-inline-comment --path "src/foo.py" --line 42 --body "Consider using LBYL here"
```

### Options

| Option   | Required | Description                                        |
| -------- | -------- | -------------------------------------------------- |
| `--path` | Yes      | File path relative to repo root                    |
| `--line` | Yes      | Line number to comment on                          |
| `--body` | Yes      | Comment text                                       |
| `--side` | No       | `LEFT` or `RIGHT` for diff side (default: `RIGHT`) |

### Examples

**Simple comment:**

```bash
erk exec post-pr-inline-comment --path "src/foo.py" --line 42 \
  --body "This should use LBYL pattern instead of try/except"
```

**Comment on removed line (left side of diff):**

```bash
erk exec post-pr-inline-comment --path "src/foo.py" --line 42 --side LEFT \
  --body "Why was this removed? It handled the edge case."
```
