# Context

The file listing printed by `_log_learn_pr_files` uses 5-space indentation, making the filenames appear too far right. User wants 4-space indent to match the surrounding output style.

# Change

**File:** `src/erk/cli/commands/land_learn.py:569`

```python
# Before
user_output(f"     {path}  ({_format_size(size)})")

# After
user_output(f"    {path}  ({_format_size(size)})")
```

# Verification

Run `erk land` on a PR with session XML files and confirm the file listing is indented 4 spaces.
