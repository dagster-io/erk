---
completed_steps: 0
steps:
- completed: false
  text: '1. **Required**: `@click.pass_context` for commands that access filesystem/context'
- completed: false
  text: '2. **Required**: Use `require_cwd(ctx)` instead of `Path.cwd()`'
- completed: false
  text: '3. **Exception**: Hook scripts with `@logged_hook`/`@project_scoped` are
    acceptable'
- completed: false
  text: '4. **Exception**: Pure utility commands (stdin/stdout only) don''t need context'
- completed: false
  text: '1. **Forbidden**: `from __future__ import annotations`'
- completed: false
  text: 1. `mark_step.py` - Add decorator, import `require_cwd`, replace line 67
- completed: false
  text: 2. `get_progress.py` - Add decorator, import `require_cwd`, replace line 64
- completed: false
  text: 3. `post_plan_comment.py` - Add decorator, import `require_cwd`, replace line
    96
- completed: false
  text: 4. `check_impl.py` - Add decorator, import `require_cwd`, replace line 52
- completed: false
  text: 5. `get_closing_text.py` - Add decorator, import `require_cwd`, replace line
    42
- completed: false
  text: 6. `create_worker_impl_from_issue.py` - Add decorator, import `require_cwd`,
    replace line 55
- completed: false
  text: 1. `impl_signal.py` - Replace 5 occurrences with `require_cwd(ctx)`
- completed: false
  text: 2. `create_extraction_branch.py` - Replace line 52
- completed: false
  text: 3. `post_start_comment.py` - Replace lines 77, 125
- completed: false
  text: 4. `impl_init.py` - Replace line 54
- completed: false
  text: 5. `post_pr_comment.py` - Replace lines 108, 130
total_steps: 16
---

# Progress Tracking

- [ ] 1. **Required**: `@click.pass_context` for commands that access filesystem/context
- [ ] 2. **Required**: Use `require_cwd(ctx)` instead of `Path.cwd()`
- [ ] 3. **Exception**: Hook scripts with `@logged_hook`/`@project_scoped` are acceptable
- [ ] 4. **Exception**: Pure utility commands (stdin/stdout only) don't need context
- [ ] 1. **Forbidden**: `from __future__ import annotations`
- [ ] 1. `mark_step.py` - Add decorator, import `require_cwd`, replace line 67
- [ ] 2. `get_progress.py` - Add decorator, import `require_cwd`, replace line 64
- [ ] 3. `post_plan_comment.py` - Add decorator, import `require_cwd`, replace line 96
- [ ] 4. `check_impl.py` - Add decorator, import `require_cwd`, replace line 52
- [ ] 5. `get_closing_text.py` - Add decorator, import `require_cwd`, replace line 42
- [ ] 6. `create_worker_impl_from_issue.py` - Add decorator, import `require_cwd`, replace line 55
- [ ] 1. `impl_signal.py` - Replace 5 occurrences with `require_cwd(ctx)`
- [ ] 2. `create_extraction_branch.py` - Replace line 52
- [ ] 3. `post_start_comment.py` - Replace lines 77, 125
- [ ] 4. `impl_init.py` - Replace line 54
- [ ] 5. `post_pr_comment.py` - Replace lines 108, 130