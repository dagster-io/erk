---
completed_steps: 0
steps:
- completed: false
  text: 1. `@kit_json_command` (1 command) - auto JSON serialization, auto schema
    docs, no context
- completed: false
  text: 2. Manual pattern (8+ commands) - `@click.pass_context` + manual `json.dumps()`
    + `SchemaCommand`
- completed: false
  text: 1. Automatically apply `@click.pass_context`
- completed: false
  text: 2. Inject `ctx` as first positional argument to wrapped function
- completed: false
  text: '3. Add `exit_on_error: bool = True` parameter'
- completed: false
  text: 1. Replace `@click.command(...)` + `@click.pass_context` with `@kit_json_command(...)`
- completed: false
  text: 2. Remove manual `json.dumps(asdict(result))` calls - just return the result
- completed: false
  text: 3. Remove manual `raise SystemExit(...)` for final return - decorator handles
    it
- completed: false
  text: 4. For graceful degradation commands, add `exit_on_error=False`
- completed: false
  text: 1. **find-project-dir.py** - No context, exit_on_error=True
- completed: false
  text: 2. **parse-issue-reference.py** - Already done, just add ctx parameter
- completed: false
  text: 3. **mark-impl-started.py** - Context needed, exit_on_error=False
- completed: false
  text: 4. **mark-impl-ended.py** - Context needed, exit_on_error=False
- completed: false
  text: 5. **post-start-comment.py** - Context needed, exit_on_error=False
- completed: false
  text: 6. **post-pr-comment.py** - Context needed, exit_on_error=False
- completed: false
  text: 7. **update-dispatch-info.py** - Context needed, exit_on_error=False
- completed: false
  text: 8. **get-pr-commit-message.py** - No context, exit_on_error=True
- completed: false
  text: 1. **Early returns with errors:** Commands that have multiple error paths
    should use the new pattern - just return the error dataclass early. The decorator
    handles serialization and exit codes.
- completed: false
  text: 2. **Complex control flow (mark_impl_started/ended):** These commands have
    many try/except blocks. The migration will simplify these by making each error
    case just return an error dataclass.
- completed: false
  text: 3. **Commands that don't need context:** They still get `ctx` as first parameter
    but can ignore it. This maintains consistency.
total_steps: 20
---

# Progress Tracking

- [ ] 1. `@kit_json_command` (1 command) - auto JSON serialization, auto schema docs, no context
- [ ] 2. Manual pattern (8+ commands) - `@click.pass_context` + manual `json.dumps()` + `SchemaCommand`
- [ ] 1. Automatically apply `@click.pass_context`
- [ ] 2. Inject `ctx` as first positional argument to wrapped function
- [ ] 3. Add `exit_on_error: bool = True` parameter
- [ ] 1. Replace `@click.command(...)` + `@click.pass_context` with `@kit_json_command(...)`
- [ ] 2. Remove manual `json.dumps(asdict(result))` calls - just return the result
- [ ] 3. Remove manual `raise SystemExit(...)` for final return - decorator handles it
- [ ] 4. For graceful degradation commands, add `exit_on_error=False`
- [ ] 1. **find-project-dir.py** - No context, exit_on_error=True
- [ ] 2. **parse-issue-reference.py** - Already done, just add ctx parameter
- [ ] 3. **mark-impl-started.py** - Context needed, exit_on_error=False
- [ ] 4. **mark-impl-ended.py** - Context needed, exit_on_error=False
- [ ] 5. **post-start-comment.py** - Context needed, exit_on_error=False
- [ ] 6. **post-pr-comment.py** - Context needed, exit_on_error=False
- [ ] 7. **update-dispatch-info.py** - Context needed, exit_on_error=False
- [ ] 8. **get-pr-commit-message.py** - No context, exit_on_error=True
- [ ] 1. **Early returns with errors:** Commands that have multiple error paths should use the new pattern - just return the error dataclass early. The decorator handles serialization and exit codes.
- [ ] 2. **Complex control flow (mark_impl_started/ended):** These commands have many try/except blocks. The migration will simplify these by making each error case just return an error dataclass.
- [ ] 3. **Commands that don't need context:** They still get `ctx` as first parameter but can ignore it. This maintains consistency.