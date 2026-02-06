---
title: Update Roadmap Step Command
read_when:
  - working with objective roadmap tables, updating step PR references, implementing plan-save workflow
---

# Update Roadmap Step Command

`erk exec update-roadmap-step` updates one or more step PR cells in an objective's roadmap table.

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
# Single step
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --pr <PR_REF>

# Multiple steps
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --step <STEP_ID> ... --pr <PR_REF>
```

### Examples

**Single step updates:**

```bash
# Set step to plan phase
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"

# Mark step as completed
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"

# Clear PR reference
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

**Multi-step updates:**

```bash
# Update multiple steps with same PR (single API call)
erk exec update-roadmap-step 6697 --step 5.1 --step 5.2 --step 5.3 --pr "plan #6759"

# Update steps across different phases
erk exec update-roadmap-step 6697 --step 1.1 --step 2.3 --pr "#6800"
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

### Single Step (Legacy Format)

When updating a single step, the command maintains backward-compatible output:

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

### Multiple Steps (New Format)

When updating multiple steps, the output includes a `steps` array with per-step results:

**All steps successful:**

```json
{
  "success": true,
  "issue_number": 6697,
  "new_pr": "plan #6759",
  "url": "https://github.com/owner/repo/issues/6697",
  "steps": [
    { "step_id": "5.1", "success": true, "previous_pr": null },
    { "step_id": "5.2", "success": true, "previous_pr": null },
    { "step_id": "5.3", "success": true, "previous_pr": null }
  ]
}
```

**Partial failure (some steps not found):**

```json
{
  "success": false,
  "issue_number": 6697,
  "new_pr": "plan #6759",
  "url": "https://github.com/owner/repo/issues/6697",
  "steps": [
    { "step_id": "5.1", "success": true, "previous_pr": null },
    { "step_id": "9.9", "success": false, "error": "step_not_found" },
    { "step_id": "5.3", "success": true, "previous_pr": null }
  ]
}
```

Note: When using multiple steps, the command makes a **single GitHub API call** with all successful replacements batched together.

## Exit Codes

The command always exits 0. Check the JSON `success` field for pass/fail:

| Scenario                         | Exit Code | JSON `success` | JSON Error Type      |
| -------------------------------- | --------- | -------------- | -------------------- |
| All steps updated                | 0         | `true`         | N/A                  |
| Issue not found                  | 0         | `false`        | `issue_not_found`    |
| No roadmap table in issue body   | 0         | `false`        | `no_roadmap`         |
| Any step ID not found in roadmap | 0         | `false`        | `step_not_found`     |
| Replacement failed (regex error) | 0         | `false`        | `replacement_failed` |

Callers should always parse the JSON output and check `success` rather than relying on exit codes.

## Implementation Notes

- Shared parsing logic lives in `objective_roadmap_shared.py`
- Step lookup works across all phases in the roadmap
- PR cell replacement uses regex pattern matching
- Status cell is always reset to "-" for inference

## Related Documentation

- [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md)
