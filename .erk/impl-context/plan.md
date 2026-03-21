# Fix: `source <(erk ... --script)` outputs path instead of content

## Context

`source <(erk slot co BRANCH --script) && erk implement` doesn't work. The `cd` to the worktree happens in a subprocess and doesn't persist, so `erk implement` runs in the original directory on `master`.

**Root cause:** `ScriptResult.output_for_script_handler()` outputs the temp file **path** to stdout. With process substitution `<(...)`, the shell sources a virtual file containing just the path string, executing it as a subprocess instead of in the current shell.

**Why the manual flow works:** `source /path/to/activate.sh` directly sources the file contents in the current shell.

**Inconsistency:** The codebase uses two competing patterns:
- `source <(erk ... --script)` — newer code (PrNextSteps, CLI docstrings) — **broken** with path output
- `source "$(erk ... --script)"` — older code (TUI, cmux, docs) — works with path output

The fix: output script **content** to stdout, standardize on `source <(...)` everywhere.

## Implementation (Red/Green TDD)

### Cycle 1: RED — Core fix test

**Write failing test** in `tests/core/test_script_result_output.py`:
- Modify `test_output_for_script_handler_routes_to_stdout` to assert output equals `content` not `path`
- `assert output == "#!/bin/bash\necho 'test'"` (the `content` field from line 17)
- Run test → RED (currently outputs path)

**GREEN** — `packages/erk-shared/src/erk_shared/core/script_writer.py`:
- Line 72: `machine_output(str(self.path), nl=False)` → `machine_output(self.content, nl=False)`
- Run test → GREEN

**Cleanup** — Update docstrings in same file (lines 31-55) and `script_error.py` docstrings

### Cycle 2: RED — Land script test

**Write failing test** in `tests/unit/cli/test_activation.py`:
- Modify `test_render_land_script_content` (line 1102) to assert `'source <(erk land --script "$@")'` instead of `cat` bridge
- Run test → RED

**GREEN** — `src/erk/cli/activation.py` (lines 387-400):
- `render_land_script()`: `source <(cat "$(erk land --script "$@")")` → `source <(erk land --script "$@")`
- Run test → GREEN

### Cycle 3: RED — TUI pattern migration tests

**Write failing tests** — update assertions in:
- `tests/tui/commands/test_registry.py:319, 897`
- `tests/tui/commands/test_execute_command.py:106`
- `tests/tui/app/test_actions.py:312`
- `tests/tui/app/test_plan_detail_screen.py:305`
- `tests/unit/services/test_plan_list_service.py:416`
- All: `source "$(erk ...)"` → `source <(erk ...)`
- Run tests → RED

**GREEN** — migrate source code:
- `src/erk/tui/commands/registry.py` lines 101, 134
- `src/erk/tui/screens/plan_detail_screen.py` lines 368, 377, 686
- `src/erk/cli/commands/exec/scripts/cmux_checkout_workspace.py` lines 118, 120
- Run tests → GREEN

### Cycle 4: Cleanup pass

- `tests/unit/cli/commands/land/test_cleanup_and_navigate.py:880`: rename `script_path_output` → `script_output`
- Update documentation:
  - `docs/learned/cli/shell-activation-pattern.md`
  - `docs/learned/cli/tripwires.md:117`
  - `docs/learned/architecture/pr-footer-validation.md:58,68`
  - `docs/learned/planning/next-steps-output.md:34`
  - `.claude/skills/cmux/SKILL.md:156,210,211`

### Final: Run full CI

`make fast-ci` → all green
