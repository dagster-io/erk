# Delete update-plan-remote-session exec script

## Context

The `update-plan-remote-session` exec script is a legacy artifact. Its functionality was consolidated into the generic `update-plan-header` command in PR #7842. The old script still exists and is still called from the CI workflow `plan-implement.yml`. This plan completes the migration by replacing the CI caller and deleting all traces of the old script.

## Changes

### 1. Migrate CI workflow caller

**File:** `.github/workflows/plan-implement.yml` (lines 296-300)

Replace the old invocation:

```yaml
erk exec update-plan-remote-session \
  --plan-id "$PLAN_ID" \
  --run-id "$RUN_ID" \
  --session-id "$SESSION_ID" \
  --branch-name "$BRANCH_NAME"
```

With the equivalent `update-plan-header` call using positional PLAN_ID and key=value pairs. The timestamp must be generated explicitly since `update-plan-header` does not auto-generate timestamps (unlike the old script which called `time.now()`):

```yaml
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
erk exec update-plan-header "$PLAN_ID" \
  "last_remote_impl_at=$TIMESTAMP" \
  "last_remote_impl_run_id=$RUN_ID" \
  "last_remote_impl_session_id=$SESSION_ID" \
  "branch_name=$BRANCH_NAME"
```

The step name ("Update plan header with remote impl info") and env block remain unchanged. The `run:` block is the only thing that changes.

**Important difference in error behavior:** The old script exited 0 on all errors (graceful degradation). The new `update-plan-header` exits 1 on errors. However, the step already has `continue-on-error: true` (line 288), so this difference is harmless — CI will not fail either way.

### 2. Delete the exec script

**File to delete:** `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py`

This is the entire 147-line file. Delete it completely.

### 3. Delete the test file

**File to delete:** `tests/unit/cli/commands/exec/scripts/test_update_plan_remote_session.py`

This is the entire 282-line test file. Delete it completely.

### 4. Remove import and registration from exec group

**File:** `src/erk/cli/commands/exec/group.py`

Remove the import (lines 163-165):
```python
from erk.cli.commands.exec.scripts.update_plan_remote_session import (
    update_plan_remote_session,
)
```

Remove the registration (line 265):
```python
exec_group.add_command(update_plan_remote_session, name="update-plan-remote-session")
```

### 5. Remove from erk-exec reference.md

**File:** `.claude/skills/erk-exec/reference.md`

Remove the command table row (line 103):
```
| `update-plan-remote-session`      | Update plan-header metadata with remote session artifact location.          |
```

Remove the full reference section (lines 1258-1271):
```
### update-plan-remote-session

Update plan-header metadata with remote session artifact location.

**Usage:** `erk exec update-plan-remote-session`

**Options:**

| Flag            | Type    | Required | Default        | Description                                  |
| --------------- | ------- | -------- | -------------- | -------------------------------------------- |
| `--plan-id`     | INTEGER | Yes      | Sentinel.UNSET | Plan identifier to update                    |
| `--run-id`      | TEXT    | Yes      | Sentinel.UNSET | GitHub Actions run ID                        |
| `--session-id`  | TEXT    | Yes      | Sentinel.UNSET | Claude Code session ID                       |
| `--branch-name` | TEXT    | No       | -              | Branch name to store in plan-header metadata |
```

### 6. Remove from plan-backend-migration.md

**File:** `docs/learned/planning/plan-backend-migration.md` (line 164)

Remove the source code reference table row:
```
| `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` | LBYL pattern with error output             |
```

## Files NOT changing

- `src/erk/cli/commands/exec/scripts/update_plan_header.py` — no changes needed; it already supports all required functionality
- `packages/erk-shared/` — no changes to shared libraries
- `CHANGELOG.md` — per project rules, never modify directly

## Verification

1. `ruff check src/ tests/` — no lint errors
2. `ty check` — no type errors
3. `pytest tests/unit/cli/commands/exec/scripts/` — existing tests for other exec scripts still pass
4. `grep -r "update.plan.remote.session" src/ tests/ .github/ .claude/ docs/` — zero remaining references (only `.impl/` and `.worker-impl/` prompt files may reference it)