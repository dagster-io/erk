# Log learn PR file inventory after creation

## Context

When `erk land` creates a learn PR (via `_create_learn_pr_impl` in `land_learn.py`), it currently logs:
1. Session discovery summary (counts, types, sizes)
2. A success message with the learn plan number and URL

The user wants to also see a list of all files committed to the learn PR, with their paths and sizes. This provides visibility into exactly what content was pushed, especially the session XML files that are embedded alongside `plan.md` and `ref.json`.

Currently, the file inventory is opaque — the user sees session discovery stats but not the actual files committed to the PR branch.

## Changes

### File: `src/erk/cli/commands/land_learn.py`

**1. Add a new function `_log_learn_pr_files` that displays the file inventory.**

After the `create_plan_draft_pr` call succeeds in `_create_learn_pr_impl`, we have access to:
- `plan_content` (the plan markdown body)
- `xml_files` dict (path → content, from `_log_session_discovery`)

The committed files are always:
- `.erk/impl-context/plan.md` — the plan content
- `.erk/impl-context/ref.json` — the metadata ref
- Any entries from `xml_files` (e.g., `.erk/impl-context/sessions/impl-{id}.xml`)

Add a function with this signature:

```python
def _log_learn_pr_files(
    *,
    plan_content: str,
    xml_files: dict[str, str],
) -> None:
```

This function should:
1. Build a list of `(path, size_kb)` tuples for all committed files
2. Compute sizes from the string content: `len(content.encode("utf-8"))` for the actual byte size
3. For `ref.json`, reconstruct the approximate size (it's small, ~50-100 bytes — build the ref_data dict the same way `_create_learn_pr_impl` does is not practical since it's already committed). Instead, estimate from the known structure or just report it with a fixed small size. **Better approach**: accept a `ref_json_content` parameter too, or compute the files dict the same way `create_plan_draft_pr` does.

**Revised approach**: Instead of reconstructing the files, pass the complete `files` dict that was committed. This means building the files dict *before* calling `create_plan_draft_pr` and passing it to both the PR creation function and the logging function.

**Implementation details:**

In `_create_learn_pr_impl`, after building `plan_content` and `xml_files`, and after `create_plan_draft_pr` returns success, add a call to the new logging function. Build the full files dict inline:

```python
import json

# After result.success check:
if result.success:
    # Build the complete file inventory for logging
    ref_data: dict[str, str | int | None] = {
        "provider": "github-draft-pr",
        "title": f"Learn: {plan_result.title}",
    }
    all_files: dict[str, str] = {
        f"{IMPL_CONTEXT_DIR}/plan.md": plan_content,
        f"{IMPL_CONTEXT_DIR}/ref.json": json.dumps(ref_data, indent=2),
    }
    if xml_files:
        all_files.update(xml_files)
    _log_learn_pr_files(files=all_files)
```

Wait — this duplicates the ref.json construction logic from `create_plan_draft_pr`. That's fragile.

**Better revised approach**: Simply log from `plan_content` + `xml_files` since those are the *significant* files. The `ref.json` is always tiny (~60 bytes) and not particularly interesting to the user. Log it as a known constant-size entry.

**Final approach**:

```python
def _log_learn_pr_files(
    *,
    plan_content: str,
    xml_files: dict[str, str],
) -> None:
    """Log the files committed to the learn plan PR with paths and sizes."""
    files: list[tuple[str, int]] = []

    # plan.md
    plan_bytes = len(plan_content.encode("utf-8"))
    files.append((f"{IMPL_CONTEXT_DIR}/plan.md", plan_bytes))

    # ref.json (always present, small metadata file)
    # Approximate size — exact content constructed by create_plan_draft_pr
    files.append((f"{IMPL_CONTEXT_DIR}/ref.json", 60))

    # Session XML files
    for path, content in sorted(xml_files.items()):
        file_bytes = len(content.encode("utf-8"))
        files.append((path, file_bytes))

    # Log file inventory
    total_bytes = sum(size for _, size in files)
    user_output(f"  📦 {len(files)} file(s) committed ({_format_size(total_bytes)}):")
    for path, size in files:
        user_output(f"     {path}  ({_format_size(size)})")


def _format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    return f"{size_bytes // 1024:,} KB"
```

**2. Call `_log_learn_pr_files` from `_create_learn_pr_impl` after the success message.**

In the `if result.success:` block, after the existing `user_output` calls for the success message and URL, add:

```python
_log_learn_pr_files(plan_content=plan_content, xml_files=xml_files)
```

This outputs the file list right after the learn plan creation confirmation, so the user sees:
```
✓ Created learn plan #8500 for plan #8496
  https://github.com/dagster-io/erk/pull/8500
  📦 4 file(s) committed (209 KB):
     .erk/impl-context/plan.md  (1 KB)
     .erk/impl-context/ref.json  (60 B)
     .erk/impl-context/sessions/planning-2d92ece3.xml  (77 KB)
     .erk/impl-context/sessions/impl-870afbf1.xml  (132 KB)
```

### File: `tests/unit/cli/commands/land/test_land_learn.py`

**3. Add tests for the new `_log_learn_pr_files` function.**

Add the import of the new function to the test imports:
```python
from erk.cli.commands.land_learn import (
    ...
    _log_learn_pr_files,
)
```

Add these test cases:

**`test_log_learn_pr_files_shows_plan_and_ref`**: Call `_log_learn_pr_files` with empty `xml_files`. Assert output contains `plan.md`, `ref.json`, `2 file(s)`, and byte sizes.

**`test_log_learn_pr_files_includes_session_xml_files`**: Call with a dict of 2 XML files. Assert output contains all 4 files (plan.md + ref.json + 2 XML), correct paths, and `4 file(s)`.

**`test_log_learn_pr_files_shows_sizes_in_kb_for_large_files`**: Create a large XML content string (>1024 bytes). Assert the output shows "KB" for that file.

**4. Update the existing `test_creates_pr_and_shows_success` test.**

This test calls `_create_learn_pr_impl` and checks stderr. After the change, it will also see the file inventory output. Add an assertion that the file inventory appears:
```python
assert "file(s) committed" in captured.err
assert "plan.md" in captured.err
```

### File: `src/erk/cli/commands/land_learn.py` — Additional import

Add `import json` at the top if not already present — actually checking the existing imports: `json` is not imported in this file currently. However, we don't actually need json since we're not reconstructing ref.json content. The `_log_learn_pr_files` function only needs `IMPL_CONTEXT_DIR` (already imported) and `user_output` (already imported).

No new imports needed.

## Files NOT Changing

- `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` — The PR creation logic stays the same. We log from the caller's perspective using data already available.
- `src/erk/cli/commands/land_pipeline.py` — Pipeline steps unchanged.
- `src/erk/cli/commands/land_cmd.py` — CLI command unchanged.
- Any other files — This is a pure output/logging change in one file.

## Implementation Details

### Key Decisions

1. **Log after success, not before**: Only show the file inventory when the PR was actually created successfully. If creation fails, the files were never committed.

2. **Approximate ref.json size**: Rather than reconstructing the exact ref.json content (which duplicates logic from `create_plan_draft_pr`), use a fixed approximate size (~60 bytes). The ref.json is always a small metadata file and its exact size is not important to the user.

3. **Use `user_output` for consistency**: All output goes through `user_output` (which writes to stderr), consistent with all other land command output.

4. **Sort XML files by path**: Ensures deterministic output order for session files.

5. **Size formatting**: Use `_format_size` helper — bytes for files <1KB, KB for larger files. This matches the existing KB formatting used in session discovery logging.

### Edge Cases

- **No XML files**: When no sessions are discovered, `xml_files` is empty. The output will show just plan.md and ref.json (2 files).
- **Multi-chunk sessions**: Sessions that produce multiple XML chunks will appear as separate files (e.g., `impl-{id}-part1.xml`, `impl-{id}-part2.xml`). Each is logged individually.

## Verification

1. Run the existing tests to ensure no regressions:
   ```
   pytest tests/unit/cli/commands/land/test_land_learn.py -v
   ```

2. Run the new tests to verify file inventory logging works correctly.

3. Run type checking:
   ```
   ty check src/erk/cli/commands/land_learn.py
   ```

4. Run linting:
   ```
   ruff check src/erk/cli/commands/land_learn.py
   ```