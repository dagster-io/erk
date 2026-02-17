---
title: Update Roadmap Step Command
last_audited: "2026-02-15 18:50 PT"
audit_result: edited
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

When the command updates plan/PR cells, it **writes status, plan, and PR cells atomically**:

| Flag                                   | Written Status | Plan Cell   | PR Cell     | Why                                                     |
| -------------------------------------- | -------------- | ----------- | ----------- | ------------------------------------------------------- |
| `--plan #6464`                         | `in-progress`  | `#6464`     | (preserved) | Plan reference indicates active work                    |
| `--plan #6464 --pr #123`               | `in-progress`  | `#6464`     | `#123`      | PR reference without --status done means work in flight |
| `--plan #6464 --pr #123 --status done` | `done`         | `#6464`     | `#123`      | Explicit --status done confirms PR is merged            |
| `--pr ""`                              | `pending`\*    | (preserved) | `-`         | \*`in-progress` if preserved plan is non-empty          |

The command also accepts legacy `--pr "plan #NNN"` syntax, which is automatically migrated to `--plan "#NNN"`.

This differs from parse-time inference (which only fires when status is `-` or empty). Writing computed status makes the table human-readable in GitHub's UI without requiring a parse pass.

**Critical distinction:** The command computes at write time; the parser infers at read time. See [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) for the full asymmetry and trade-offs.

## Usage Pattern

```bash
# Single step — plan reference
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --plan <PLAN_REF>

# Single step — landed PR (--plan is required with --pr)
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --pr <PR_REF> --plan <PLAN_REF>

# Multiple steps
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --step <STEP_ID> ... --plan <PLAN_REF>
```

### Examples

**Single step updates:**

```bash
# Set step to plan phase
erk exec update-roadmap-step 6423 --step 1.3 --plan "#6464"

# Link PR (infers in-progress status)
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500" --plan "#6464"

# Mark step as done with landed PR
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500" --plan "#6464" --status done

# Clear PR reference (resets to pending)
erk exec update-roadmap-step 6423 --step 1.3 --pr ""
```

Output is structured JSON with `success`, `issue_number`, `step_id`, `previous_pr`, `new_pr`, and `url` fields.

```bash
# Update multiple steps with same plan (single API call)
erk exec update-roadmap-step 6697 --step 5.1 --step 5.2 --step 5.3 --plan "#6759"
```

The command follows erk's discriminated union pattern for error returns:

| Exit Code | Scenario                 | JSON `error` Field   |
| --------- | ------------------------ | -------------------- |
| 0         | Success                  | N/A                  |
| 0         | Issue doesn't exist      | `issue_not_found`    |
| 0         | No roadmap table in body | `no_roadmap`         |
| 0         | Step ID not in roadmap   | `step_not_found`     |
| 0         | Regex replacement failed | `replacement_failed` |

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, update_roadmap_step -->

All error paths exit with code 0 but include typed error fields for programmatic handling. See `update_roadmap_step()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` for the LBYL guard sequence.

## Body Inclusion: --include-body

The `--include-body` flag causes the command to include the fully-mutated issue body in the JSON output as `updated_body`. This eliminates the need for callers to re-fetch the issue body after step updates.

```bash
# Get the updated body back in the JSON output
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500" --plan "#6464" --include-body
```

**Output with `--include-body` (single step):**

```json
{
  "success": true,
  "issue_number": 6423,
  "step_id": "1.3",
  "previous_plan": null,
  "new_plan": null,
  "previous_pr": null,
  "new_pr": "#6500",
  "url": "https://github.com/owner/repo/issues/6423",
  "updated_body": "# Objective: Build Feature X\n\n## Roadmap\n..."
}
```

**Output with `--include-body` (multiple steps):**

```json
{
  "success": true,
  "issue_number": 6697,
  "new_plan": null,
  "new_pr": "#555",
  "url": "https://github.com/owner/repo/issues/6697",
  "steps": [...],
  "updated_body": "# Objective: Build Feature X\n\n## Roadmap\n..."
}
```

The `updated_body` field is only included when:

- `--include-body` is passed
- The update was successful (all steps for multi-step, the single step for single-step)

On failure paths, the field is omitted regardless of the flag.

## Parameter Semantics: --plan and --pr

The command uses separate `--plan` and `--pr` flags for the two lifecycle stages:

| Flag                                        | Status Computed | Lifecycle Stage                             |
| ------------------------------------------- | --------------- | ------------------------------------------- |
| `--plan "#6464"`                            | `in-progress`   | Step has an active plan issue               |
| `--plan "#6464" --pr "#6500"`               | `in-progress`   | PR reference (not confirmed merged)         |
| `--plan "#6464" --pr "#6500" --status done` | `done`          | Step has a confirmed landed PR              |
| `--pr ""`                                   | `pending`\*     | Clear PR; \*`in-progress` if plan preserved |

When `--pr` is set, `--plan` must also be explicitly provided (error: `plan_required_with_pr`). Use `--plan "#NNN"` to preserve or `--plan ""` to clear. The legacy `--pr "plan #NNN"` syntax is still accepted and automatically migrated to `--plan "#NNN"`.

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

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_refs_in_body -->

The regex in `_replace_step_refs_in_body()` supports both four-column (legacy) and five-column tables:

```
| step_id | description | status | plan | pr |   (5-col, canonical)
| step_id | description | status | pr |           (4-col, legacy)
```

When updating a 4-col table, the command upgrades the header to 5-col automatically. Step lookup works across all phases (the parser flattens phases into a single step list). See `_find_step_refs()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`.

### Shared Parsing Logic

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, parse_roadmap -->

Both `update-roadmap-step` and `erk objective check` use `parse_roadmap()` from `erk_shared.gateway.github.metadata.roadmap`. The shared module defines `RoadmapStep` and `RoadmapPhase` dataclasses — the canonical representation of parsed roadmap state.

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
subprocess.run(["erk", "exec", "update-roadmap-step", str(issue), "--step", "1.3", "--pr", "#123", "--plan", "#456"])
```

The command is designed for programmatic invocation — JSON output is machine-parsable.

## Related Documentation

- [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) — write-time vs parse-time status computation
- [Roadmap Status System](../../objectives/roadmap-status-system.md) — two-tier status resolution rules
- [Roadmap Parser](../../objectives/roadmap-parser.md) — parsing and validation logic
