# Plan: Ensure erk kit scripts abide by AGENTS.md

## Summary

Audit of 52 Python scripts in `packages/erk-kits/src/erk_kits/data/kits/erk/scripts/erk/` against the new AGENTS.md standards reveals **11 files with `Path.cwd()` violations** and **1 file with a Python 3.13 type annotation violation**.

## Standards Being Applied

From `AGENTS.md`:
1. **Required**: `@click.pass_context` for commands that access filesystem/context
2. **Required**: Use `require_cwd(ctx)` instead of `Path.cwd()`
3. **Exception**: Hook scripts with `@logged_hook`/`@project_scoped` are acceptable
4. **Exception**: Pure utility commands (stdin/stdout only) don't need context

From `dignified-python-313`:
1. **Forbidden**: `from __future__ import annotations`

---

## Violations Found

### Category 1: `Path.cwd()` Violations (11 files)

| File | Lines | Fix Required |
|------|-------|--------------|
| `impl_signal.py` | 96, 132, 134, 259, 261 | Replace with `require_cwd(ctx)` |
| `create_extraction_branch.py` | 52 | Replace with `require_cwd(ctx)` |
| `mark_step.py` | 67 | Add `@click.pass_context`, use `require_cwd(ctx)` |
| `post_start_comment.py` | 77, 125 | Replace with `require_cwd(ctx)` |
| `get_progress.py` | 64 | Add `@click.pass_context`, use `require_cwd(ctx)` |
| `post_plan_comment.py` | 96 | Add `@click.pass_context`, use `require_cwd(ctx)` |
| `check_impl.py` | 52 | Add `@click.pass_context`, use `require_cwd(ctx)` |
| `impl_init.py` | 54 | Replace with `require_cwd(ctx)` |
| `get_closing_text.py` | 42 | Add `@click.pass_context`, use `require_cwd(ctx)` |
| `post_pr_comment.py` | 108, 130 | Replace with `require_cwd(ctx)` |
| `create_worker_impl_from_issue.py` | 55 | Add `@click.pass_context`, use `require_cwd(ctx)` |

### Category 2: Python 3.13 Type Annotation Violation (1 file)

| File | Line | Issue |
|------|------|-------|
| `get_pr_review_comments.py` | 26 | `from __future__ import annotations` - FORBIDDEN |

### Category 3: Documentation Update Required (1 file)

| File | Change |
|------|--------|
| `AGENTS.md` | Add exception for hook scripts using `@logged_hook`/`@project_scoped` |

---

## Files Already Compliant

- **33+ commands** properly use `@click.pass_context` with context helpers
- **7 pure utilities** legitimately don't need context (stdin/stdout processing only):
  - `issue_title_to_filename.py`, `parse_issue_reference.py`, `format_error.py`
  - `validate_plan_content.py`, `wrap_plan_in_metadata_block.py`
  - `get_pr_body_footer.py`, `format_success_output.py`
- **3 hook scripts** use special decorators (acceptable per user decision):
  - `exit_plan_mode_hook.py`, `session_id_injector_hook.py`, `tripwires_reminder_hook.py`

---

## Implementation Steps

### Step 1: Update AGENTS.md with Hook Exception
Add section documenting that hook scripts may use `@logged_hook`/`@project_scoped` instead of `@click.pass_context`.

### Step 2: Fix Python 3.13 Violation
**File**: `get_pr_review_comments.py`
- Remove line 26: `from __future__ import annotations`

### Step 3: Fix Commands Missing `@click.pass_context` (6 files)
For each file, add the decorator and replace `Path.cwd()`:

1. `mark_step.py` - Add decorator, import `require_cwd`, replace line 67
2. `get_progress.py` - Add decorator, import `require_cwd`, replace line 64
3. `post_plan_comment.py` - Add decorator, import `require_cwd`, replace line 96
4. `check_impl.py` - Add decorator, import `require_cwd`, replace line 52
5. `get_closing_text.py` - Add decorator, import `require_cwd`, replace line 42
6. `create_worker_impl_from_issue.py` - Add decorator, import `require_cwd`, replace line 55

### Step 4: Fix Commands With `@click.pass_context` But Using `Path.cwd()` (5 files)
These already have context but bypass it:

1. `impl_signal.py` - Replace 5 occurrences with `require_cwd(ctx)`
2. `create_extraction_branch.py` - Replace line 52
3. `post_start_comment.py` - Replace lines 77, 125
4. `impl_init.py` - Replace line 54
5. `post_pr_comment.py` - Replace lines 108, 130

### Step 5: Run Type Checker
Run `uv run pyright` on modified files to verify no type errors introduced.

---

## Related Documentation

- Skills to load: `dignified-python-313` (for type annotation standards)
- Reference: `.erk/docs/agent/kits/dependency-injection.md`