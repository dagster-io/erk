# Harden one-shot-plan to reject invalid prompts

## Context

When a garbled/invalid prompt is committed to `.erk/impl-context/prompt.md`, Claude correctly identifies it as nonsensical but exits 0 without writing any output files. The workflow then fails at "Verify plan outputs exist" with a confusing error. Claude should explicitly reject invalid prompts by writing a rejection result.

## Changes

### 1. `.claude/commands/erk/system/one-shot-plan.md`

Add a **Step 1.5: Validate the Prompt** between reading the prompt and loading context:

- After reading `prompt.md`, assess whether it contains a valid, actionable task description
- If the prompt is clearly invalid (garbled terminal output, empty, nonsensical, not a task description), skip to a rejection flow:
  1. Write `.erk/impl-context/plan-result.json` with `{"rejected": true, "reason": "<brief explanation>"}`
  2. Stop — do not proceed to exploration, planning, or saving

### 2. `.github/workflows/one-shot.yml`

Modify the **"Verify plan outputs exist"** step (lines 160-171) to check for rejection before checking for plan.md:

```yaml
- name: Verify plan outputs exist
  if: steps.plan.outputs.plan_success == 'true'
  id: verify
  run: |
    if [ -f .erk/impl-context/plan-result.json ]; then
      REJECTED=$(jq -r '.rejected // false' .erk/impl-context/plan-result.json)
      if [ "$REJECTED" = "true" ]; then
        REASON=$(jq -r '.reason // "No reason provided"' .erk/impl-context/plan-result.json)
        echo "::warning::Plan rejected: $REASON"
        echo "rejected=true" >> $GITHUB_OUTPUT
        exit 0
      fi
    fi
    if [ ! -f .erk/impl-context/plan.md ]; then
      echo "::error::Planning succeeded but .erk/impl-context/plan.md not found"
      exit 1
    fi
    if [ ! -f .erk/impl-context/plan-result.json ]; then
      echo "::error::Planning succeeded but .erk/impl-context/plan-result.json not found"
      exit 1
    fi
    echo "Plan outputs found"
    echo "rejected=false" >> $GITHUB_OUTPUT
```

Gate all downstream steps on `steps.verify.outputs.rejected != 'true'`:
- "Read plan result" step
- "Validate plan format" step
- "Register one-shot plan" step
- "Update objective roadmap node" step
- "Commit plan to branch" step

Add a step to update the plan issue on rejection (if `plan_issue_number` is set):

```yaml
- name: Update plan on rejection
  if: steps.verify.outputs.rejected == 'true' && inputs.plan_issue_number != ''
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
    PLAN_ISSUE_NUMBER: ${{ inputs.plan_issue_number }}
  run: |
    REASON=$(jq -r '.reason // "Invalid prompt"' .erk/impl-context/plan-result.json)
    gh issue close "$PLAN_ISSUE_NUMBER" --comment "Plan rejected by planning agent: $REASON"
```

## Files to modify

- `.claude/commands/erk/system/one-shot-plan.md`
- `.github/workflows/one-shot.yml`

## Verification

1. Read both modified files to confirm correctness
2. Run `prettier --check` on the workflow YAML
3. Manually verify logic: if Claude writes `{"rejected": true, "reason": "..."}`, the workflow should warn, close the plan issue, and exit cleanly without failing
