# Delete `erk objective reconcile` command

## Rationale

`reconcile` and `next-plan` both launch Claude with `/erk:objective-next-plan`. The only added value of `reconcile` is pre-validation (issue exists + has `erk-objective` label). That validation isn't worth a separate command — the skill itself can fail gracefully if the issue is invalid.

**Scope:** Delete the CLI command only. The `erk launch objective-reconcile` GitHub Actions workflow is unrelated (remote dispatch) and stays.

## Changes

### 1. Delete `reconcile_cmd.py`
- Delete `src/erk/cli/commands/objective/reconcile_cmd.py`

### 2. Remove from command group
- `src/erk/cli/commands/objective/__init__.py` — remove the import and `register_with_aliases` call for `reconcile_objectives`

### 3. Delete test file
- Delete `tests/commands/objective/test_reconcile_cmd.py`

### 4. Update docs referencing the CLI command
- `docs/learned/cli/objective-commands.md` — remove `reconcile` entry
- `docs/learned/cli/command-group-structure.md` — remove if listed
- `docs/learned/cli/workflow-commands.md` — remove if it references the CLI command (not the workflow)

## Verification

- `devrun`: `ruff check src/erk/cli/commands/objective/`
- `devrun`: `pytest tests/commands/objective/ -x`
- `devrun`: `ty check src/erk/cli/commands/objective/__init__.py`