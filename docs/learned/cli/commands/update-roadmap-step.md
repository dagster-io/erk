---
title: Update Roadmap Step Command
read_when:
  - working with objective roadmap tables, updating step PR references, implementing plan-save workflow
---

# Update Roadmap Step Command

`erk exec update-roadmap-step` updates a single step's PR cell in an objective's roadmap table.

## Command Rationale

**Why this command exists instead of direct body manipulation:**

The alternative approach would be "fetch body → parse markdown table → find step row → surgically edit the PR cell → write entire body back". That's ~15 lines of fragile ad-hoc Python that every caller (skills, hooks, scripts) must duplicate.

Encoding the roadmap update logic once in a tested CLI command provides:

- No duplicated table-parsing logic across callers
- Testable edge cases (step not found, no roadmap, clearing PR)
- Atomic mental model: "update step 1.3's PR to X"
- Resilient to roadmap format changes (one command updates, not N sites)

## Usage

```bash
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --pr <PR_REF>
```

### Examples

```bash
# Set step to plan phase
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"

# Mark step as completed
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"

# Clear PR reference
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

## Status Inference Semantics

When the command updates a step's PR cell, it **resets the status cell to "-"**. This triggers the status inference logic in `parse_roadmap()`:

- `#123` → status: `done`
- `plan #123` → status: `in_progress`
- Empty → status: `pending`

This ensures the status column always reflects the current state based on the PR column.

## Integration with Plan-Save Workflow

This command is used in Step 3.5 of the plan-save workflow to link a plan issue to its parent objective:

1. Plan issue is created
2. Objective roadmap is fetched
3. `update-roadmap-step` sets the step's PR cell to `plan #<issue_number>`
4. Status is automatically inferred as `in_progress`

## Output Format

The command outputs JSON:

```json
{
  "success": true,
  "issue_number": 6423,
  "step_id": "1.3",
  "previous_pr": "",
  "new_pr": "plan #6464",
  "url": "https://github.com/owner/repo/issues/6423"
}
```

## Error Codes

The command returns distinct exit codes for different failure scenarios:

| Code | Scenario                         | JSON Error Type      |
| ---- | -------------------------------- | -------------------- |
| 0    | Success - step updated           | N/A                  |
| 1    | Issue not found                  | `issue_not_found`    |
| 1    | No roadmap table in issue body   | `no_roadmap`         |
| 1    | Step ID not found in roadmap     | `step_not_found`     |
| 1    | Replacement failed (regex error) | `replacement_failed` |

## Implementation Notes

- Shared parsing logic lives in `objective_roadmap_shared.py`
- Step lookup works across all phases in the roadmap
- PR cell replacement uses regex pattern matching
- Status cell is always reset to "-" for inference

## Related Documentation

- [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md)
