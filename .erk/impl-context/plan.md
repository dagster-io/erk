# Move objective-update-with-landed-pr to erk/system/

## Context

Move the command from `.claude/commands/erk/objective-update-with-landed-pr.md` to `.claude/commands/erk/system/objective-update-with-landed-pr.md`. This changes the invocation path from `/erk:objective-update-with-landed-pr` to `/erk:system:objective-update-with-landed-pr`.

## Steps

### 1. Move the file

- `git mv .claude/commands/erk/objective-update-with-landed-pr.md .claude/commands/erk/system/objective-update-with-landed-pr.md`

### 2. Update self-references in the moved file

- `.claude/commands/erk/system/objective-update-with-landed-pr.md` — update heading and usage block

### 3. Update Python source references

- `src/erk/cli/commands/objective_helpers.py:132` — command string construction
- `src/erk/cli/commands/objective_helpers.py:152` — manual retry message

### 4. Update the calling command

- `.claude/commands/erk/land.md:141` — references the command

### 5. Update tests

- `tests/commands/land/test_objective_update.py:159`
- `tests/unit/cli/commands/exec/scripts/test_land_execute_objective_detection.py:289`
- `tests/unit/cli/commands/exec/scripts/test_objective_update_after_land.py:53,90`

### 6. Update documentation

- `docs/learned/planning/agent-delegation.md:30`
- `docs/learned/planning/objective-update-after-land.md:29`
- `docs/learned/cli/slash-command-llm-turn-optimization.md:44,47`
- `docs/learned/objectives/roadmap-mutation-patterns.md:11`
- `docs/learned/objectives/objective-lifecycle.md` (multiple lines: 183, 219, 221, 293, 323, 368, 506, 515)
- `docs/learned/objectives/tripwires.md:91`

### 7. Update state tracking

- `.erk/state.toml:48` — artifact file path

## Verification

- `git grep 'erk:objective-update-with-landed-pr'` should return zero hits for the old path (without `system:`)
- `git grep 'erk:system:objective-update-with-landed-pr'` should show all updated references
- Run tests: `pytest tests/commands/land/ tests/unit/cli/commands/exec/scripts/test_land_execute_objective_detection.py tests/unit/cli/commands/exec/scripts/test_objective_update_after_land.py`
