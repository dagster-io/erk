# Plan: Show per-file metadata in manifest output

## Context

When `erk land` creates a learn plan, the manifest output shows session-level metadata but doesn't show which XML files belong to each session. The file inventory is printed separately later (in `_log_learn_pr_files`), making it hard to understand which artifacts came from which session. The user also wants the manifest source (branch + file path) displayed.

## Changes

### File: `src/erk/cli/commands/land_learn.py`

#### 1. Update `_log_session_summary_from_manifest` to accept `xml_files` and `plan_id`

- Add parameters: `xml_files: dict[str, str]`, `plan_id: str`
- Print manifest source line before the table: `Manifest: planned-pr-context/{plan_id} .erk/sessions/manifest.json`
- After each session row, add indented file rows showing filename + size
- Use the manifest entry's `files` list to find matching keys in `xml_files` dict
- Compute per-file size from `xml_files[path]` content length
- Display files dimmed/indented under their parent session

#### 2. Update call site in `_collect_session_material` (line 158)

Pass `xml_files` and `plan_id` to the updated function:
```python
_log_session_summary_from_manifest(manifest, xml_files=xml_files, plan_id=plan_id)
```

#### 3. Remove redundant file listing from `_log_learn_pr_files`

Remove the session XML file lines from `_log_learn_pr_files` since they're now shown in the manifest. Keep only plan.md and ref.json in that function (or remove the function entirely if those are better shown elsewhere).

### Target output

```
  Manifest: planned-pr-context/8953 :: .erk/sessions/manifest.json (2 sessions)
Stage  Session      Source  Turns  Duration  Size
impl   none...      local   2      8 min     1,284 KB -> 175 KB
                                              impl-none-7fc19510-...-part1.xml  (71 KB)
                                              impl-none-7fc19510-...-part2.xml  (68 KB)
                                              impl-none-7fc19510-...-part3.xml  (17 KB)
                                              impl-none-7fc19510-...-part4.xml  (6 KB)
                                              impl-none-7fc19510-...-part5.xml  (10 KB)
impl   7fc19510...  remote  2      9 min     1,302 KB -> 180 KB
                                              impl-7fc19510-...-part1.xml  (71 KB)
                                              impl-7fc19510-...-part2.xml  (68 KB)
                                              impl-7fc19510-...-part3.xml  (22 KB)
                                              impl-7fc19510-...-part4.xml  (6 KB)
                                              impl-7fc19510-...-part5.xml  (10 KB)
```

## Verification

- Run: `pytest tests/unit/cli/commands/land/ -k land_learn -x`
- Existing tests should pass (function signature change may require updating test calls)
- Visual verification of output format by inspecting the table construction
