# Add generic `erk exec update-plan-header` command

## Context

PR #7836 was saved without `--objective-issue=7823`, so its plan-header metadata lacks the `objective_issue` field. The TUI reads this field to display objective associations — without it, the PR shows "-". There's no command to fix this because each plan-header field has its own dedicated exec command (`update-dispatch-info`, `update-lifecycle-stage`, `update-plan-remote-session`), and none handles `objective_issue`.

The backend already does full schema validation: `update_metadata()` in `draft_pr.py:474` merges fields, protects immutables, and validates against `PlanHeaderSchema`. The specialized commands are doing redundant work on top.

## Plan

### Step 1: Create `update_plan_header.py`

**File**: `src/erk/cli/commands/exec/scripts/update_plan_header.py`

Generic command:
```
erk exec update-plan-header <plan_id> key1=value1 key2=value2 ...
```

- `plan_id`: Click argument (str)
- `fields`: Click argument (variadic, `nargs=-1`)
- Parse each field as `key=value`, error if no `=`
- Type coercion: `"null"` → `None`, valid int string → `int`, else `str`
- LBYL: reject if zero fields provided
- Call `backend.update_metadata(repo_root, plan_id, metadata=parsed_dict)`
- Backend handles: merge with existing data, immutable field protection (`schema_version`, `created_at`, `created_by`), full `PlanHeaderSchema` validation (field names, types, enums for `lifecycle_stage`/`learn_status`/`last_session_source`, positive int checks, format checks)
- Catch `PlanHeaderNotFoundError` and `RuntimeError`, output JSON error
- On `ValueError` from schema validation, output JSON error with the validation message
- Success JSON: `{"success": true, "plan_id": "<id>", "fields_updated": ["key1", "key2"]}`

### Step 2: Delete `update_dispatch_info.py`

**Delete files:**
- `src/erk/cli/commands/exec/scripts/update_dispatch_info.py`
- `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py`

No workflow callers. No Python callers beyond group.py registration.

### Step 3: Delete `update_lifecycle_stage.py`

**Delete files:**
- `src/erk/cli/commands/exec/scripts/update_lifecycle_stage.py`
- `tests/unit/cli/commands/exec/scripts/test_update_lifecycle_stage.py`

### Step 4: Update `group.py`

**File**: `src/erk/cli/commands/exec/group.py`

- Remove imports of `update_dispatch_info` and `update_lifecycle_stage`
- Remove their `add_command` registrations
- Add import of `update_plan_header`
- Add `exec_group.add_command(update_plan_header, name="update-plan-header")`

### Step 5: Update workflow caller

**File**: `.github/workflows/one-shot.yml:128`

Change:
```yaml
erk exec update-lifecycle-stage --plan-id "$PLAN_ISSUE_NUMBER" --stage planning
```
To:
```yaml
erk exec update-plan-header "$PLAN_ISSUE_NUMBER" lifecycle_stage=planning
```

### Step 6: Update documentation references

- `docs/learned/planning/lifecycle.md` — update `update-dispatch-info` and `update-lifecycle-stage` references to `update-plan-header`
- `.claude/skills/erk-exec/reference.md` — replace both entries with `update-plan-header`

### Step 7: Add tests

**File**: `tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`

Following the pattern from `test_update_dispatch_info.py` (reuse `make_plan_header_body` and `make_issue_info` helpers):

1. `test_update_single_field` — set `objective_issue=7823`, verify in metadata
2. `test_update_multiple_fields` — set `lifecycle_stage=implementing` + `objective_issue=7823`
3. `test_overwrites_existing` — existing value gets replaced
4. `test_null_coercion` — `objective_issue=null` → sets None
5. `test_int_coercion` — `objective_issue=7823` → stored as int 7823
6. `test_string_preserved` — `branch_name=my-branch` → stays string
7. `test_schema_validation_rejects_unknown_field` — `bogus_field=x` → exit 1
8. `test_schema_validation_rejects_invalid_lifecycle_stage` — `lifecycle_stage=bogus` → exit 1
9. `test_immutable_field_protected` — `created_by=hacker` → silently ignored by backend
10. `test_no_fields_provided` — exit 1
11. `test_invalid_field_format` — `no-equals-sign` → exit 1
12. `test_plan_not_found` — exit 1
13. `test_no_plan_header_block` — exit 1

### Step 8: Fix PR #7836 and objective #7823

```bash
erk exec update-plan-header 7836 objective_issue=7823
erk exec update-objective-node 7823 --node 1.1 --plan "#7836"
erk exec update-objective-node 7823 --node 1.2 --plan "#7836"
erk exec update-objective-node 7823 --node 1.3 --plan "#7836"
```

## Key Files

| File | Role |
|------|------|
| `src/erk/cli/commands/exec/scripts/update_dispatch_info.py` | Delete (replaced) |
| `src/erk/cli/commands/exec/scripts/update_lifecycle_stage.py` | Delete (replaced) |
| `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py` | Delete |
| `tests/unit/cli/commands/exec/scripts/test_update_lifecycle_stage.py` | Delete |
| `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` | Keep (has timestamp computation) |
| `src/erk/cli/commands/exec/group.py` | Update registrations |
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py:436` | Existing `update_metadata()` — does merge + validation |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py:447` | `PlanHeaderSchema` — full field/type/enum validation |
| `.github/workflows/one-shot.yml:128` | Update caller |

## Verification

1. `uv run pytest tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`
2. `ruff check` and `ty` on modified files
3. Verify deleted test files no longer exist and no imports reference them
4. Run Step 8 commands to fix PR #7836 and objective #7823
5. Confirm TUI shows "#7823" in objective column for PR #7836
