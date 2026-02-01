# New batch command: resolve-review-threads

## Summary

Create a new `resolve-review-threads` (plural) exec command that accepts JSON stdin to resolve multiple threads in one invocation. The existing `resolve-review-thread` command stays unchanged.

## Interface

```bash
echo '[{"thread_id": "PRRT_1", "comment": "Fixed"}, {"thread_id": "PRRT_2"}]' | \
  erk exec resolve-review-threads
```

- Reads JSON array from stdin
- Each item: `{"thread_id": str, "comment": str | null}`
- Processes each thread sequentially (comment + resolve)
- Reuses internal helpers from `resolve_review_thread.py`

**Output:**
```json
{
  "success": true,
  "results": [
    {"success": true, "thread_id": "PRRT_1", "comment_added": true},
    {"success": true, "thread_id": "PRRT_2", "comment_added": false}
  ]
}
```
- Top-level `success` is true only if ALL items succeeded
- Each result has same shape as current single-thread output (`ResolveThreadSuccess` / `ResolveThreadError`)

## Files to Create/Modify

### 1. Refactor existing file: `src/erk/cli/commands/exec/scripts/resolve_review_thread.py`

Extract a reusable `_resolve_single(github, repo_root, thread_id, comment)` function that returns `ResolveThreadSuccess | ResolveThreadError` (no sys.exit, no click.echo). The existing command function calls this and handles output/exit as before.

### 2. New file: `src/erk/cli/commands/exec/scripts/resolve_review_threads.py`

- Click command `resolve-review-threads` (no options, reads stdin)
- Reads and validates JSON array from `click.get_text_stream('stdin')`
- Validates each item has `thread_id` (string), optional `comment` (string|null)
- Loops calling `_resolve_single()` from the existing module
- Collects results into `BatchResolveResult` dataclass
- Outputs JSON, exits 0

New dataclass:
```python
@dataclass(frozen=True)
class BatchResolveResult:
    success: bool  # True only if all succeeded
    results: list[dict[str, object]]  # asdict() of each individual result
```

### 3. Register in `src/erk/cli/commands/exec/group.py`

- Import `resolve_review_threads` from new module
- Add `exec_group.add_command(resolve_review_threads, name="resolve-review-threads")`

### 4. New tests: `tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py`

Test cases:
- Batch resolve two threads successfully
- Batch with comments on some threads
- Partial failure (one thread fails, others succeed) → top-level success=false
- Empty array → success=true, results=[]
- Invalid JSON stdin → error output
- Missing thread_id field → error output

## Verification

```bash
uv run pytest tests/unit/cli/commands/exec/scripts/test_pr_review_comments.py  # existing tests pass
uv run pytest tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py  # new tests pass
```