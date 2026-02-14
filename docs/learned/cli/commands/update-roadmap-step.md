---
title: Update Roadmap Step Command
read_when:
  - working with objective roadmap tables, updating step PR references, implementing plan-save workflow
tripwires:
  - action: "parsing roadmap tables to update PR cells"
    warning: "Use the update-roadmap-step command instead of manual parsing. The command encodes table structure knowledge once rather than duplicating it across callers."
  - action: "expecting status to auto-update after manual PR edits"
    warning: "Only the update-roadmap-step command writes computed status. Manual edits require explicitly setting status to '-' to enable inference on next parse."
---

# Update Roadmap Step Command

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
# Link step to plan issue
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"

# Mark step as done with landed PR
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"

# Clear PR reference (resets to pending)
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

Output is structured JSON with `success`, `issue_number`, `step_id`, `previous_pr`, `new_pr`, and `url` fields.

## Error Handling Strategy

The command follows erk's discriminated union pattern for error returns:

| Exit Code | Scenario                 | JSON `error` Field   |
| --------- | ------------------------ | -------------------- |
| 0         | Success                  | N/A                  |
| 1         | Issue doesn't exist      | `issue_not_found`    |
| 1         | No roadmap table in body | `no_roadmap`         |
| 1         | Step ID not in roadmap   | `step_not_found`     |
| 1         | Regex replacement failed | `replacement_failed` |

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, update_roadmap_step -->

All error paths exit with code 1 but include typed error fields for programmatic handling. See `update_roadmap_step()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py:107-182` for the LBYL guard sequence.

## Plan-Save Integration Point

The command's primary caller is the plan-save workflow (Step 3.5):

1. Agent creates plan issue → gets issue number
2. Fetch parent objective → extract roadmap
3. **Call update-roadmap-step** → sets step's PR to `plan #<issue>`
4. Status automatically written as `in-progress`

This integration is why the command returns structured JSON — upstream scripts need the URL and previous state for logging.

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
