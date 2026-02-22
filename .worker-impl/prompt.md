Implement step 3.3 of objective #7775: Delete update-plan-remote-session exec script — remaining artifact from the consolidation into update-plan-header (PR #7842).

Objective: #7775 — Clean Up Legacy Plan Infrastructure
Node: 3.3

Changes needed:

1. Migrate CI workflow caller in `.github/workflows/plan-implement.yml` (around line 296): Replace `erk exec update-plan-remote-session` with `erk exec update-plan-header` using positional PLAN_ID and key=value pairs. The timestamp must be generated explicitly with `date -u`. Always pass `branch_name`.

2. Delete `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py`

3. Delete `tests/unit/cli/commands/exec/scripts/test_update_plan_remote_session.py`

4. Remove import and registration from `src/erk/cli/commands/exec/group.py` (lines 163-165 import, line 265 registration)

5. Remove entry from `.claude/skills/erk-exec/reference.md` (command table line 107 and full reference section lines 1262-1275)

6. Remove source code reference row from `docs/learned/planning/plan-backend-migration.md` (line 164)

Verification: ruff check, ty check, pytest tests/unit/cli/commands/exec/scripts/, grep for zero remaining references.

