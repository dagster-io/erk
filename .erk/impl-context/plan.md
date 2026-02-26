# Fix: Pass plan PR number to objective roadmap update in plan-save

## Context

When `/erk:plan-save` updates an objective's roadmap (Step 3.5), it calls:
```bash
erk exec update-objective-node <objective-issue> --node "$step_id" --pr "" --status in_progress
```

`--pr ""` clears the PR field, losing the plan PR number that was just created. The plan number is available from the JSON output parsed earlier in the skill, but never gets passed through.

## Change

**File:** `.claude/commands/erk/plan-save.md` — line 120

Replace:
```bash
erk exec update-objective-node <objective-issue> --node "$step_id" --pr "" --status in_progress
```

With:
```bash
erk exec update-objective-node <objective-issue> --node "$step_id" --pr "#<plan_number>" --status in_progress
```

Where `<plan_number>` is the plan number extracted from the plan-save JSON output in Step 2. This follows the same `"#<number>"` format used by other callers (e.g., `objective-reevaluate` uses `--pr "#<pr-number>"`).

Single line change. No other files affected.

## Verification

- Read the updated skill and confirm the command template references `plan_number`
- Check that `update-objective-node` accepts `--pr "#123"` format (confirmed: sets PR cell and infers `in_progress` status)
