# Phase 3: CLI Command with Dry-Run

**Part of Objective #5934, Phase 3**

Create `erk objective reconcile` command with `--dry-run` support to test reconciliation logic against live objectives without mutating state.

## Goal

When run with `--dry-run`, the command should:
1. List all objectives with `erk-objective` + `auto-advance` labels
2. For each objective, call `determine_action()` from the reconciler core
3. Display the planned action for each objective in a Rich table
4. Exit without making any changes

When run without `--dry-run`, the same behavior but with actual execution (Phase 4 work - out of scope).

## Implementation Phases

### Phase A: Core CLI Command (Steps 3.1, 3.2)

**New file: `src/erk/cli/commands/objective/reconcile_cmd.py`**

Create the reconcile command with:
- `@click.command("reconcile")`
- `--dry-run` flag (required for Phase 3 - always operates in dry-run mode)
- Repository context discovery
- Uses `ctx.issues.list_issues()` with `labels=["erk-objective", "auto-advance"]`
- For each objective, calls `determine_action(ctx.prompt_executor, issue.body)`
- Displays results in Rich table with columns: #, Title, Action, Step, Reason

**Output format:**
```
Reconciling auto-advance objectives...

#     Title                              Action       Step    Reason
5934  Objective Reconciliation Loop      create_plan  3.1     Previous steps complete
5940  Another Objective                  none         -       All steps done
```

At the end:
```
[DRY RUN] Would create 1 plan(s). Run without --dry-run to execute.
```

### Phase B: Wire into CLI Group (Step 3.4)

**Modify: `src/erk/cli/commands/objective/__init__.py`**

- Import `reconcile_objectives` from `reconcile_cmd.py`
- Register with `register_with_aliases(objective_group, reconcile_objectives)`

### Phase C: Tests (Step 3.3)

**New file: `tests/commands/objective/test_reconcile_cmd.py`**

Tests using FakePromptExecutor and FakeGitHubIssues:

1. `test_reconcile_dry_run_shows_planned_actions()` - With objectives that have pending steps
2. `test_reconcile_no_auto_advance_objectives()` - Handles empty list gracefully
3. `test_reconcile_inference_error()` - Handles LLM errors gracefully
4. `test_reconcile_mixed_results()` - Multiple objectives with different action types

## Key Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/objective/reconcile_cmd.py` | Create |
| `src/erk/cli/commands/objective/__init__.py` | Modify |
| `tests/commands/objective/test_reconcile_cmd.py` | Create |

## Dependencies

Existing code to use:
- `erk_shared.objectives.reconciler.determine_action()` - Core reconciliation logic
- `erk_shared.objectives.types.ReconcileAction` - Result type
- `erk_shared.prompt_executor.abc.PromptExecutor` - LLM interface (via `ctx.prompt_executor`)
- `ctx.issues.list_issues()` - Query objectives with labels

## Design Decisions

1. **Dry-run only for Phase 3**: The command will only support `--dry-run` mode initially. Live execution is Phase 4 scope.

2. **Single action per objective**: Display what would happen for each objective, consistent with "single action per objective per run" design in the objective.

3. **No mutations in Phase 3**: The command reads objectives and displays planned actions but doesn't create plans or update roadmaps yet.

4. **Rich table output**: Consistent with `erk objective list` output style.

## Verification

1. Run `erk objective reconcile --dry-run` in a repo with auto-advance objectives
2. Verify output shows planned actions for each objective
3. Verify no issues are modified (check GitHub)
4. Run unit tests: `pytest tests/commands/objective/test_reconcile_cmd.py -v`

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Docs: `docs/learned/cli/output-styling.md`, `docs/learned/testing/testing.md`