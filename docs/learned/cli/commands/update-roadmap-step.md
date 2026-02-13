---
title: Update Roadmap Step Command
read_when:
  - working with objective roadmap tables, updating step PR references, implementing plan-save workflow
  - implementing CLI commands that accept multiple values for the same parameter
  - deciding between multi-option and JSON stdin batch patterns
tripwires:
  - action: "parsing roadmap tables to update PR cells"
    warning: "Use the update-roadmap-step command instead of manual parsing. The command encodes table structure knowledge once rather than duplicating it across callers."
  - action: "expecting status to auto-update after manual PR edits"
    warning: "Only the update-roadmap-step command writes computed status. Manual edits require explicitly setting status to '-' to enable inference on next parse."
---

# Update Roadmap Step Command

`erk exec update-roadmap-step` updates one or more step PR cells in an objective's roadmap table.

## Why This Command Exists

The alternative to `erk exec update-roadmap-step` is inline markdown table manipulation: fetch body → parse table → find row by step ID → regex-replace PR cell → update body. That's ~15 lines of fragile ad-hoc code duplicated across every caller (skills, hooks, scripts).

**Why encoding this once wins:**

1. **No duplicated table parsing** — regex patterns and step lookup logic live in one place
2. **Atomic mental model** — "update step 1.3's PR to X" instead of "parse, find, replace, validate"
3. **Testable edge cases** — step not found, no roadmap, clearing PR all have test coverage
4. **Format resilience** — roadmap table structure changes propagate once, not to N call sites

The command is infrastructure for workflow integration, not an interactive tool.

## Status Computation Semantics

When the command updates a PR cell, it **writes both the status and PR cells atomically**:

| PR Value     | Written Status | Why                                   |
| ------------ | -------------- | ------------------------------------- |
| `#123`       | `done`         | PR reference indicates landed work    |
| `plan #6464` | `in-progress`  | Plan prefix indicates active planning |
| `""` (empty) | `pending`      | Clearing PR resets to initial state   |

This differs from parse-time inference (which only fires when status is `-` or empty). Writing computed status makes the table human-readable in GitHub's UI without requiring a parse pass.

**Critical distinction:** The command computes at write time; the parser infers at read time. See [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) for the full asymmetry and trade-offs.

## Usage Pattern

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

# Mark step as done with landed PR
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"

# Clear PR reference (resets to pending)
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

**Multi-step updates:**

```bash
# Update multiple steps with same PR (single API call)
erk exec update-roadmap-step 6697 --step 5.1 --step 5.2 --step 5.3 --pr "plan #6759"

# Update steps across different phases
erk exec update-roadmap-step 6697 --step 1.1 --step 2.3 --pr "#6800"
```

## Multi-Step Usage

The command accepts multiple `--step` flags to update several roadmap steps in a single invocation:

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, update_roadmap_step -->

This pattern is optimized for GitHub API efficiency: the command fetches the issue body once, applies all step updates in memory, then writes the body once. This avoids N API calls for N steps.

## Parameter Semantics: --pr Accepts Plans and PRs

The `--pr` parameter accepts two semantic types, reflecting the lifecycle of roadmap cells:

| Input          | Status Computed | Lifecycle Stage               |
| -------------- | --------------- | ----------------------------- |
| `"plan #6464"` | `in-progress`   | Step has an active plan issue |
| `"#6500"`      | `done`          | Step has a landed PR          |
| `""` (empty)   | `pending`       | Clear the reference           |

This naming is admittedly confusing — `--pr` accepts plan references despite the parameter name. The parameter was named for the common case (linking landed PRs) but the overloading enables the full lifecycle. A future refactor may rename this to `--ref` for clarity.

**Why both are accepted:** The roadmap tracks the full lifecycle: empty (pending) -> plan issue (in-progress) -> landed PR (done). Using a single parameter for all stages keeps the CLI simple. The `plan ` prefix is the discriminator for status inference.

See [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) for the write-time vs parse-time distinction.

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

### Table Structure Assumptions

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_pr_in_body -->

The regex in `_replace_step_pr_in_body()` expects four-column tables:

```
| step_id | description | status | pr |
```

Step lookup works across all phases (the parser flattens phases into a single step list). See `_find_step_pr()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py:48-60`.

### Shared Parsing Logic

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py, parse_roadmap -->

Both `update-roadmap-step` and `erk objective check` use `parse_roadmap()` from `objective_roadmap_shared.py`. The shared module defines `RoadmapStep` and `RoadmapPhase` dataclasses — the canonical representation of parsed roadmap state.

## Plan-Save Integration Point

The command's primary caller is the plan-save workflow (Step 3.5):

1. Agent creates plan issue → gets issue number
2. Fetch parent objective → extract roadmap
3. **Call update-roadmap-step** → sets step's PR to `plan #<issue>`
4. Status automatically written as `in-progress`

This integration is why the command returns structured JSON — upstream scripts need the URL and previous state for logging.

## Anti-Pattern: Manual Table Surgery

**DON'T** fetch body, run regex, update body directly:

```python
# WRONG: Duplicates table structure knowledge
body = github.get_issue(...).body
updated = re.sub(r"(\| 1.3 \|.*\|.*\|).*(\|)", r"\1 #123 \2", body)
github.update_issue_body(...)
```

**WHY:** This assumes four-column structure, doesn't handle status computation, doesn't validate step exists, and duplicates logic already tested in the command.

**DO** call the command:

```python
subprocess.run(["erk", "exec", "update-roadmap-step", str(issue), "--step", "1.3", "--pr", "#123"])
```

The command is designed for programmatic invocation — JSON output is machine-parsable.

## Related Documentation

- [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) — write-time vs parse-time status computation
- [Roadmap Status System](../../objectives/roadmap-status-system.md) — two-tier status resolution rules
- [Roadmap Parser](../../objectives/roadmap-parser.md) — parsing and validation logic
