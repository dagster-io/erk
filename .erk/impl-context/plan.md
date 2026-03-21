# Reopen Contested Resolved Threads (Push-Down Replan)

> **Replans:** #9262

## Context

When `erk:pr-address` resolves a PR review thread, it adds a reply with attribution text and resolves the thread. If a reviewer pushes back (adds comments after resolution), the thread stays resolved and subsequent pr-address runs never see it (resolved threads are filtered out by default).

This plan adds detection and reopening of "contested" threads — resolved threads with unaddressed reviewer comments after the last pr-address attribution marker.

**What changed since original plan:** The `refac-cli-push-down` pattern now formalizes the approach of moving mechanical computation from prompts into tested CLI commands. The original plan already created an exec script (good), but the pr-address.md changes can be made even more minimal — just call the command and let JSON output drive behavior.

## Investigation Findings

### Current State (master)
- 0% of #9262 is implemented on master
- `resolve_review_thread` ABC at `abc.py:679`, real at `real.py:2122`
- `RESOLVE_REVIEW_THREAD_MUTATION` at `graphql_queries.py:53`
- `_format_resolution_comment` at `resolve_review_thread.py:64` — no marker yet
- pr-address.md has Phases 0-6, no Phase 0.5

### Corrections to Original Plan
- Line numbers shifted slightly due to recent master commits
- `resolve_review_thread` is at abc.py:679 (not 671), real.py:2122 (not 2086)

## Implementation Steps

### Step 1: Add GraphQL mutation

**File:** `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`

Add `UNRESOLVE_REVIEW_THREAD_MUTATION` after `RESOLVE_REVIEW_THREAD_MUTATION` (after line 60):

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

**ABC** (`packages/erk-shared/src/erk_shared/gateway/github/abc.py`) — add after `resolve_review_thread` (after line 693):

```python
@abstractmethod
def unresolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
    """Unresolve a PR review thread."""
    ...
```

**Real** (`packages/erk-shared/src/erk_shared/gateway/github/real.py`) — add after `resolve_review_thread` (after line 2157). Mirror resolve exactly, using `UNRESOLVE_REVIEW_THREAD_MUTATION` and checking `data.unresolveReviewThread.thread.isResolved` is `False`.

**Dry-Run** (`packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`) — add no-op returning `True` after resolve method.

**Fake** (`tests/fakes/gateway/github.py`):
- Constructor param: `unresolve_thread_failures: set[str] | None = None`
- Mutable state: `self._unresolved_thread_ids: set[str] = set()`
- Method: check failures, track in `_unresolved_thread_ids`, return `True`
- Property: `unresolved_thread_ids` for test assertions
- Update `get_pr_review_threads`: thread unresolved if `t.id in self._unresolved_thread_ids`

### Step 3: Add HTML marker to resolution comments

**File:** `src/erk/cli/commands/exec/scripts/resolve_review_thread.py`

Add constant at module level (after imports, before dataclasses):

```python
PR_ADDRESS_MARKER = "<!-- erk:pr-address-resolved -->"
```

Update `_format_resolution_comment` (line 64) to append marker:

```python
def _format_resolution_comment(comment: str) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f"{comment}\n\n_Addressed via `/erk:pr-address` at {timestamp}_\n{PR_ADDRESS_MARKER}"
```

### Step 4: New exec script

**File:** `src/erk/cli/commands/exec/scripts/reopen_contested_threads.py`

Click command `reopen-contested-threads` with optional `--pr` flag.

**Algorithm:**
1. Resolve PR number (from `--pr` or current branch)
2. Fetch all threads with `include_resolved=True`
3. Filter to resolved threads with `PR_ADDRESS_MARKER` in any comment
4. For each, check if any comments exist after the last marker comment → contested
5. Call `github.unresolve_review_thread` for each contested thread
6. Output JSON result

**Pure helper functions** (testable without gateway):
- `_has_marker(body: str) -> bool`
- `_find_contested_threads(threads: list[PRReviewThread]) -> list[PRReviewThread]`

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
- PR detection: `get_pr_feedback.py` (branch detection + `pr_for_branch`)
- Script structure: `resolve_review_thread.py` (similar single-operation pattern)

### Step 5: Register exec script

**File:** `src/erk/cli/commands/exec/group.py`

Import and register `reopen_contested_threads` alphabetically (between `register_one_shot_plan` and `reply_to_discussion_comment`).

### Step 6: Update pr-address command (push-down style)

**File:** `.claude/commands/erk/pr-address.md`

Add **Phase 0.5** between Phase 0 and Phase 1 — minimal, push-down style:

```markdown
### Phase 0.5: Reopen Contested Threads

```bash
erk exec reopen-contested-threads [--pr <number> if specified]
```

If `total_contested > 0`, report: "Reopened N contested threads — these will be included in classification below."
If `success` is false, warn but continue (non-blocking).
```

This is ~4 lines instead of the original plan's ~15 lines. The exec command handles all detection/filtering/unresolving logic. The agent just calls it and reports.

### Step 7: Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_reopen_contested_threads.py`

- No contested threads (attribution is last comment)
- Single contested thread (comment after attribution → gets unresolved)
- Mixed: manually resolved (no marker) vs pr-address resolved with pushback
- Unresolved threads are untouched
- Multiple attribution comments (use the last one)
- API failure during unresolve captured per-thread
- Pure function tests: `_has_marker`, `_find_contested_threads`

## Verification

1. `uv run pytest tests/unit/cli/commands/exec/scripts/test_reopen_contested_threads.py`
2. `uv run pytest tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py` (regression)
3. `uv run pytest packages/erk-shared/tests/unit/github/` (gateway)
4. `uv run ty check src/erk/cli/commands/exec/scripts/reopen_contested_threads.py`
