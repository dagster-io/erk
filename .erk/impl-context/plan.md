# Reopen Contested Resolved Threads in pr-address

## Context

When `erk:pr-address` addresses a PR review comment, it adds a reply with `_Addressed via /erk:pr-address at {timestamp}_` and resolves the thread. If a reviewer pushes back (adds more comments saying the fix isn't right), the thread stays resolved. Since `get_pr_review_threads` filters out resolved threads by default (`real.py:1922`), subsequent pr-address runs never see these contested threads.

**Goal:** At the start of pr-address, detect resolved threads that have new comments after the last pr-address attribution comment, and unresolve them so they get picked up by normal classification.

## Implementation

### Step 1: Add GraphQL mutation

**File:** `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`

Add after `RESOLVE_REVIEW_THREAD_MUTATION` (line 42):

```python
UNRESOLVE_REVIEW_THREAD_MUTATION = """mutation($threadId: ID!) {
  unresolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}"""
```

### Step 2: Add gateway method (4 places)

**ABC** (`packages/erk-shared/src/erk_shared/gateway/github/abc.py`) — add abstract method after `resolve_review_thread` (line 671):

```python
@abstractmethod
def unresolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
```

**Real** (`packages/erk-shared/src/erk_shared/gateway/github/real.py`) — add after `resolve_review_thread` (line 2086). Mirror the resolve implementation exactly, using `UNRESOLVE_REVIEW_THREAD_MUTATION` and checking `data.unresolveReviewThread.thread.isResolved` is `False`.

**Dry-Run** (`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`) — add no-op returning `True` after line 299.

**Fake** (`tests/fakes/gateway/github.py`):
- Add constructor param `unresolve_thread_failures: set[str] | None = None` (after `resolve_thread_failures` line 72)
- Add mutable state `self._unresolved_thread_ids: set[str] = set()` (after `_resolved_thread_ids` line 183)
- Implement method: check failures set, track in `_unresolved_thread_ids`, return `True`
- Add `unresolved_thread_ids` property for test assertions
- Update `get_pr_review_threads` (line 956): a thread that was unresolved should appear as unresolved:
  ```python
  is_resolved = (t.is_resolved or t.id in self._resolved_thread_ids) and t.id not in self._unresolved_thread_ids
  ```

### Step 2.5: Add HTML marker to resolution comments

**File:** `src/erk/cli/commands/exec/scripts/resolve_review_thread.py`

Update `_format_resolution_comment` (line 64-74) to append a hidden HTML marker:

```python
PR_ADDRESS_MARKER = "<!-- erk:pr-address-resolved -->"

def _format_resolution_comment(comment: str) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f"{comment}\n\n_Addressed via `/erk:pr-address` at {timestamp}_\n{PR_ADDRESS_MARKER}"
```

The marker `<!-- erk:pr-address-resolved -->` is invisible in GitHub's UI but machine-readable for detection. Export `PR_ADDRESS_MARKER` as a module-level constant so the new script can import it.

### Step 3: New exec script

**File:** `src/erk/cli/commands/exec/scripts/reopen_contested_threads.py`

Click command `reopen-contested-threads` with optional `--pr` flag.

**Algorithm:**
1. Resolve PR number (from `--pr` flag or current branch, same pattern as `get_pr_feedback.py`)
2. Fetch all threads with `include_resolved=True`
3. Filter to resolved threads only
4. For each resolved thread, scan comments for `PR_ADDRESS_MARKER` (`<!-- erk:pr-address-resolved -->`)
5. If any comments exist after the last marker comment, the thread is contested
6. Call `github.unresolve_review_thread` for each contested thread
7. Output JSON result

**Pure helper functions** (testable without gateway):
- `_has_marker(body: str) -> bool` — checks for `PR_ADDRESS_MARKER` in comment body
- `_find_contested_threads(threads: list[PRReviewThread]) -> list[PRReviewThread]` — filters resolved threads to contested ones

**Detection logic:** Only threads previously resolved by pr-address (evidenced by the HTML marker) are candidates. Manually resolved threads (no marker) are left alone.

**Output format:**
```json
{
  "success": true,
  "pr_number": 123,
  "contested_threads": [{"thread_id": "PRRT_abc", "path": "src/foo.py", "line": 42, "unresolve_success": true}],
  "total_resolved_checked": 5,
  "total_contested": 1,
  "total_reopened": 1
}
```

**Key pattern references:**
- PR detection: `get_pr_feedback.py:117-124` (branch detection + `GitHubChecks.pr_for_branch`)
- Marker constant: `resolve_review_thread.py` (`PR_ADDRESS_MARKER`)
- Script structure: `resolve_review_threads.py` (similar batch-operation pattern)

### Step 4: Register exec script

**File:** `src/erk/cli/commands/exec/group.py`

- Import `reopen_contested_threads` (alphabetically between `register_one_shot_plan` and `reply_to_discussion_comment`, ~line 137)
- Register: `exec_group.add_command(reopen_contested_threads, name="reopen-contested-threads")` (alphabetically between `register-one-shot-plan` and `reply-to-discussion-comment`, ~line 261)

### Step 5: Update pr-address command

**File:** `.claude/commands/erk/pr-address.md`

Add **Phase 0.5: Reopen Contested Threads** between Phase 0 (Mode Detection) and Phase 1 (Classify Feedback):

```markdown
### Phase 0.5: Reopen Contested Threads

Before classifying feedback, check for resolved threads with unaddressed reviewer pushback:

\```bash
erk exec reopen-contested-threads [--pr <number> if specified]
\```

If `contested_threads` is non-empty, report:
- Table of reopened threads (path, line)
- "These threads will be included in the classification below."

If empty, proceed silently. If `success` is false, warn but continue (non-blocking).
```

This step applies to both Code Review Mode and Plan File Mode (PF-1 equivalent).

### Step 6: Tests

**Exec script tests** (`tests/unit/cli/commands/exec/scripts/test_reopen_contested_threads.py`):
- No contested threads (all resolved threads have attribution as last comment)
- Single contested thread (comment after attribution -> gets unresolved)
- Mixed: some manually resolved (no attribution), some pr-address resolved with pushback
- Unresolved threads are untouched
- Multiple attribution comments in thread (use the last one)
- API failure during unresolve captured per-thread, doesn't crash

**Pure function tests** (same file):
- `_is_attribution_comment` with matching/non-matching bodies
- `_find_contested_threads` with various thread configurations

**Fake behavior test** (`tests/unit/fakes/` or inline in exec script tests):
- Unresolve tracks thread IDs
- Unresolved thread appears as unresolved in subsequent `get_pr_review_threads` fetch

## Verification

1. Run exec script tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_reopen_contested_threads.py`
2. Run fake tests if separate: `uv run pytest tests/unit/fakes/`
3. Run existing resolve tests to ensure no regressions: `uv run pytest tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py`
4. Run gateway tests: `uv run pytest packages/erk-shared/tests/unit/github/`
5. Type check: `uv run ty check src/erk/cli/commands/exec/scripts/reopen_contested_threads.py`
6. Manual: `erk exec reopen-contested-threads --pr <PR with contested threads>` against a real PR
