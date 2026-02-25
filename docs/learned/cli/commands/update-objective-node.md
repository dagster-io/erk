---
title: Update Objective Node Command
last_audited: "2026-02-25 18:00 PT"
audit_result: edited
read_when:
  - working with objective roadmap tables, updating step PR references
tripwires:
  - action: "parsing roadmap tables to update PR cells"
    warning: "Use the update-objective-node command instead of manual parsing. The command encodes table structure knowledge once rather than duplicating it across callers."
  - action: "expecting status to auto-update after manual PR edits"
    warning: "Only the update-objective-node command writes computed status. Manual edits require explicitly setting status to '-' to enable inference on next parse."
---

# Update Objective Node Command

## Why This Command Exists

The alternative to `erk exec update-objective-node` is inline YAML frontmatter manipulation: fetch body -> parse YAML -> find node -> update fields -> serialize -> update body. That's fragile ad-hoc code duplicated across every caller (skills, hooks, scripts).

**Why encoding this once wins:**

1. **No duplicated YAML parsing** -- frontmatter parsing and node lookup logic live in one place
2. **Atomic mental model** -- "update step 1.3's PR to X" instead of "parse, find, replace, validate"
3. **Testable edge cases** -- step not found, no roadmap, clearing PR all have test coverage
4. **Comment table re-rendering** -- automatically re-renders the comment table from YAML after updates
5. **Format resilience** -- roadmap structure changes propagate once, not to N call sites

The command is infrastructure for workflow integration, not an interactive tool.

## Status Computation Semantics

When the command updates PR/status cells, it **writes status and PR atomically**:

| Flag                             | Written Status | PR Cell   | Why                                          |
| -------------------------------- | -------------- | --------- | -------------------------------------------- |
| `--pr #123`                      | `in-progress`  | `#123`    | PR reference indicates active work           |
| `--pr #123 --status done`        | `done`         | `#123`    | Explicit --status done confirms PR is merged |
| `--pr #123 --status in_progress` | `in-progress`  | `#123`    | Explicit status overrides PR-based inference |
| `--pr ""`                        | `(preserved)`  | (cleared) | Clear PR reference, preserve existing status |

This differs from parse-time inference (which only fires when status is `-` or empty). Writing computed status makes the table human-readable in GitHub's UI without requiring a parse pass.

**Critical distinction:** The command computes at write time; the parser infers at read time. See [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) for the full asymmetry and trade-offs.

## Usage Pattern

```bash
# Single step -- set PR reference (marks done)
erk exec update-objective-node <ISSUE_NUMBER> --node <STEP_ID> --pr <PR_REF>

# Single step -- set PR and explicit status
erk exec update-objective-node <ISSUE_NUMBER> --node <STEP_ID> --pr <PR_REF> --status in_progress

# Multiple steps
erk exec update-objective-node <ISSUE_NUMBER> --node <STEP_ID> --node <STEP_ID> ... --pr <PR_REF>
```

### Examples

**Single step updates:**

```bash
# Link PR (infers in_progress status)
erk exec update-objective-node 6423 --node 1.3 --pr "#6500"

# Link PR with explicit status override
erk exec update-objective-node 6423 --node 1.3 --pr "#6500" --status in_progress

# Mark step as done with landed PR
erk exec update-objective-node 6423 --node 1.3 --pr "#6500" --status done

# Clear PR reference (preserves existing status)
erk exec update-objective-node 6423 --node 1.3 --pr ""
```

Output is structured JSON with `success`, `issue_number`, `node_id`, `previous_pr`, `new_pr`, and `url` fields.

```bash
# Update multiple steps with same PR (single API call)
erk exec update-objective-node 6697 --node 5.1 --node 5.2 --node 5.3 --pr "#6759"
```

The command follows erk's discriminated union pattern for error returns:

| Exit Code | Scenario                 | JSON `error` Field   |
| --------- | ------------------------ | -------------------- |
| 0         | Success                  | N/A                  |
| 0         | Issue doesn't exist      | `issue_not_found`    |
| 0         | No roadmap table in body | `no_roadmap`         |
| 0         | Step ID not in roadmap   | `node_not_found`     |
| 0         | Regex replacement failed | `replacement_failed` |

All error paths exit with code 0 but include typed error fields for programmatic handling.

## Body Inclusion: --include-body

The `--include-body` flag causes the command to include the fully-mutated issue body in the JSON output as `updated_body`. This eliminates the need for callers to re-fetch the issue body after step updates.

```bash
# Get the updated body back in the JSON output
erk exec update-objective-node 6423 --node 1.3 --pr "#6500" --include-body
```

**Output with `--include-body` (single step):**

```json
{
  "success": true,
  "issue_number": 6423,
  "node_id": "1.3",
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
  "new_pr": "#555",
  "url": "https://github.com/owner/repo/issues/6697",
  "nodes": [...],
  "updated_body": "# Objective: Build Feature X\n\n## Roadmap\n..."
}
```

## Parameter Semantics: --pr and --status

The command uses `--pr` and `--status` flags:

| Flag                                | Status Computed | Lifecycle Stage          |
| ----------------------------------- | --------------- | ------------------------ |
| `--pr "#6500" --status in_progress` | `in-progress`   | Explicit status override |
| `--pr "#6500"`                      | `in-progress`   | Step has active work     |
| `--pr "#6500" --status done`        | `done`          | Explicit confirmation    |
| `--pr ""`                           | `(preserved)`   | Clear PR reference       |

See [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) for the write-time vs parse-time distinction.

## Comment Table Re-rendering

After updating YAML frontmatter in the issue body, the command automatically re-renders the comment table using `rerender_comment_roadmap()`. This function:

1. Parses nodes from the updated YAML frontmatter
2. Groups by phase and enriches phase names from comment headers
3. Renders fresh markdown tables
4. Splices into the comment's `<!-- erk:roadmap-table -->` marker section

This ensures the comment table always reflects the current YAML state.

## Implementation Notes

### Shared Parsing Logic

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py -->

Both `update-objective-node` and `erk objective check` use `parse_roadmap()` from `erk_shared.gateway.github.metadata.roadmap`. The shared module defines `RoadmapNode` and `RoadmapPhase` dataclasses -- the canonical representation of parsed roadmap state.

## Anti-Pattern: Manual Table Surgery

**DON'T** fetch body, run regex, update body directly:

```python
# WRONG: Duplicates table structure knowledge
body = github.get_issue(...).body
updated = re.sub(r"(\| 1.3 \|.*\|.*\|).*(\|)", r"\1 #123 \2", body)
github.update_issue_body(...)
```

**WHY:** This doesn't handle status computation, doesn't validate step exists, and duplicates logic already tested in the command.

**DO** call the command:

```python
subprocess.run(["erk", "exec", "update-objective-node", str(issue), "--node", "1.3", "--pr", "#123"])
```

The command is designed for programmatic invocation -- JSON output is machine-parsable.

## Related Documentation

- [Roadmap Mutation Semantics](../../architecture/roadmap-mutation-semantics.md) -- write-time vs parse-time status computation
- [Roadmap Mutation Patterns](../../objectives/roadmap-mutation-patterns.md) -- surgical vs full-body update strategy
- [Roadmap Status System](../../objectives/roadmap-status-system.md) -- two-tier status resolution rules
- [Roadmap Parser](../../objectives/roadmap-parser.md) -- parsing and validation logic
