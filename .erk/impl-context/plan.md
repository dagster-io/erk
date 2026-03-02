# Add `modify_existing` input to one-shot.yml with conditional plan registration

## Context

This is node 1.2 of objective #8470 ("One-Shot Modification of Existing PRs"). Node 1.1 (PR #8472) added the `_dispatch_one_shot` handler in `launch_cmd.py` that dispatches the one-shot workflow with `modify_existing: "true"` in the workflow inputs. However, the `one-shot.yml` workflow currently has no `modify_existing` input defined — GitHub Actions silently ignores unknown inputs, so the flag is discarded.

This plan adds the `modify_existing` input to `one-shot.yml` and makes the plan registration step conditional on whether this is a new one-shot or a modification of an existing PR.

**Why this matters:** When modifying an existing PR, the "Register one-shot plan" step should be **skipped** because:

1. The plan entity (PR) already exists — no new plan registration is needed
2. The `register-one-shot-plan` command writes dispatch metadata and a "Queued for Implementation" comment, which are inappropriate for modifications to existing PRs
3. The lifecycle stage should not be reset to "planned" for an existing PR that may already be in a later stage

Similarly, the "Update objective roadmap node" step should be skipped in modify-existing mode since the existing PR already has its objective linkage.

## Changes

### 1. `.github/workflows/one-shot.yml` — Add `modify_existing` input and conditional steps

**Add new input** in the `workflow_dispatch.inputs` section, after `plan_only`:

```yaml
      modify_existing:
        description: "If true, modifying an existing PR (skip plan registration)"
        required: false
        type: string
        default: ""
```

Note: Use `type: string` (not boolean) because `launch_cmd.py` passes `"true"` as a string value, and GitHub Actions `workflow_dispatch` boolean inputs behave inconsistently with string `"true"`. Checking `inputs.modify_existing == 'true'` is reliable.

**Modify the "Register one-shot plan with issue and PR" step condition** (currently line 190-201):

Change the `if:` condition from:

```yaml
        if: steps.plan.outputs.plan_success == 'true' && steps.read_result.outputs.plan_id != ''
```

to:

```yaml
        if: >
          steps.plan.outputs.plan_success == 'true'
          && steps.read_result.outputs.plan_id != ''
          && inputs.modify_existing != 'true'
```

**Modify the "Update objective roadmap node" step condition** (currently line 203-218):

Change the `if:` condition from:

```yaml
        if: >
          steps.plan.outputs.plan_success == 'true'
          && steps.read_result.outputs.plan_id != ''
          && inputs.objective_issue != ''
          && inputs.node_id != ''
```

to:

```yaml
        if: >
          steps.plan.outputs.plan_success == 'true'
          && steps.read_result.outputs.plan_id != ''
          && inputs.objective_issue != ''
          && inputs.node_id != ''
          && inputs.modify_existing != 'true'
```

**Pass `modify_existing` through to plan-implement job** — this is NOT needed for node 1.2. The implement job uses `plan-implement.yml` which doesn't need to know about modify_existing; it simply implements the plan on the existing branch. The branch name and PR number are already correctly passed from `_dispatch_one_shot`.

### 2. No other files change

- `src/erk/cli/commands/launch_cmd.py` — Already passes `modify_existing: "true"` (from node 1.1). No changes needed.
- `tests/commands/launch/test_launch_cmd.py` — Already verifies `inputs["modify_existing"] == "true"`. No changes needed.
- `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` — No changes; it's simply not called in modify-existing mode.
- `.claude/commands/erk/one-shot-plan.md` — No changes; the planning command works the same regardless of modify_existing.
- `.github/workflows/plan-implement.yml` — No changes; it implements plans the same way regardless of how they were created.

## Implementation Details

### Exact edit locations in `.github/workflows/one-shot.yml`

1. **New input** — Insert after line 56 (the `plan_only` input block). Place it as the last input:

```yaml
      modify_existing:
        description: "If true, modifying an existing PR (skip plan registration)"
        required: false
        type: string
        default: ""
```

2. **Register step condition** — Find the step `"Register one-shot plan with issue and PR"` (around line 190). Add `&& inputs.modify_existing != 'true'` to the `if:` condition. Convert to multiline `>` format if not already.

3. **Objective update step condition** — Find the step `"Update objective roadmap node"` (around line 203). Add `&& inputs.modify_existing != 'true'` to the multiline `if:` condition.

### Why string type, not boolean

GitHub Actions `workflow_dispatch` has a known quirk: boolean inputs sent via API (`gh workflow run`) are serialized as strings. The `_dispatch_one_shot` handler in `launch_cmd.py` already passes `"true"` as a string. Using `type: string` with `default: ""` means:

- Normal one-shot dispatch (from `dispatch_one_shot`): input not set → empty string → conditions pass
- Modify-existing dispatch (from `_dispatch_one_shot`): `"true"` → conditions fail → registration skipped

This matches the existing pattern used by `plan_only` which is `type: boolean` but `modify_existing` comes from the API as a string, making `type: string` more reliable.

### Edge case: distinct_id

When `_dispatch_one_shot` dispatches the workflow, it does NOT pass a `distinct_id` input (check `launch_cmd.py` line 319-325). The `distinct_id` input in one-shot.yml is `required: true`, which means GitHub Actions will use an empty string. The `run-name` template `"one-shot:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"` will render with an empty suffix, which is acceptable since `distinct_id` is used for run discovery and modify-existing runs are initiated by the user directly (not through the dispatch pipeline that creates distinct_id).

**Action needed:** Add `distinct_id` to the inputs passed by `_dispatch_one_shot` in `launch_cmd.py`. Generate a random base36 string to match the existing pattern. However, this is a separate concern from node 1.2 — if the existing tests pass without it, defer this fix.

**Actually, on closer review:** `_dispatch_one_shot` calls `_dispatch_workflow` which calls `ctx.github.trigger_workflow()` directly. GitHub Actions handles missing required string inputs by using empty string. The current `distinct_id: ""` in the workflow means the `run-name` will be `"one-shot:#123:"` which is functional. No change needed for node 1.2.

## Verification

1. **Run the existing test suite** — `pytest tests/commands/launch/` should pass with no changes (this plan only modifies the workflow YAML, not Python code).

2. **Validate YAML syntax** — Ensure the workflow YAML is valid after edits. Run `python -c "import yaml; yaml.safe_load(open('.github/workflows/one-shot.yml'))"`.

3. **Manual verification of the conditional logic:**
   - For normal one-shot dispatch: `modify_existing` is empty string → `inputs.modify_existing != 'true'` is true → registration runs ✓
   - For modify-existing dispatch: `modify_existing` is `"true"` → `inputs.modify_existing != 'true'` is false → registration skipped ✓
   - For `plan_only` mode: not affected by this change ✓

4. **No Prettier/formatting checks needed** — YAML files in `.github/workflows/` are not covered by the project's Prettier configuration.

## Files NOT Changing

- `src/erk/cli/commands/launch_cmd.py` — Already correct from node 1.1
- `src/erk/cli/commands/one_shot_dispatch.py` — Normal dispatch path, unrelated
- `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` — Simply not called
- `.claude/commands/erk/one-shot-plan.md` — Planning behavior is unchanged
- `.claude/commands/erk/one-shot.md` — CLI command unchanged
- `.github/workflows/plan-implement.yml` — Implementation behavior is unchanged
- `tests/` — No new tests needed; workflow YAML changes are validated by CI
- `CHANGELOG.md` — Never modified directly