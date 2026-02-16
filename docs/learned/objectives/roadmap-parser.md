---
title: Roadmap Parser
last_audited: "2026-02-07 18:30 PT"
audit_result: edited
read_when:
  - "understanding how roadmap steps are parsed"
  - "working with objective roadmap check or update commands"
  - "debugging roadmap parsing issues"
  - "using erk objective check or erk exec update-roadmap-step"
tripwires:
  - action: "implementing roadmap parsing functionality"
    warning: "The parser is regex-based, not LLM-based. Do not reference LLM inference."
  - action: "creating or modifying roadmap step IDs"
    warning: "Step IDs should use plain numbers (1.1, 2.1), not letter format (1A.1, 1B.1)."
---

# Roadmap Parser

This document describes how erk parses and mutates objective roadmap tables using regex-based parsing.

## Overview

Erk uses deterministic regex parsing to extract structured data from objective roadmap markdown tables. Two commands expose this functionality:

- **`erk objective check`** — parse and validate a roadmap, returning human-readable or structured JSON output
- **`erk exec update-roadmap-step`** — surgically update a specific step's PR column

Both commands share the parser in `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`.

## Check Command

```bash
erk objective check <OBJECTIVE_REF>
erk objective check <OBJECTIVE_REF> --json-output
```

Fetches the objective issue body from GitHub, parses all roadmap tables, runs validation checks, and returns results. Use `--json-output` for structured JSON.

For full details on the check command, JSON schema, and validation rules, see [objective-roadmap-check.md](objective-roadmap-check.md).

### Parsing Rules

1. **Phase headers**: Matches `### Phase N: Name` (with optional letter suffix and `(N PR)` trailer)
2. **Table structure**: Expects `| Step | Description | Status | PR |` header with separator
3. **Row extraction**: Each `| id | desc | status | pr |` row becomes a `RoadmapStep`

### Validation

The parser emits warnings (not errors) for:

- Missing phase headers
- Missing or malformed table structure
- Letter-format step IDs (e.g., `1A.1` — prefer `1.1`)

## Update Command

```bash
erk exec update-roadmap-step <ISSUE_NUMBER> --step <STEP_ID> --pr <PR_REF>
```

| Flag     | Required | Example             | Description            |
| -------- | -------- | ------------------- | ---------------------- |
| `--step` | yes      | `2.1`               | Step ID to update      |
| `--pr`   | yes      | `#123`, `plan #456` | New PR reference value |

The command:

1. Fetches the issue body
2. Regex-finds the target row by step ID
3. Replaces the PR cell with the new value
4. Resets the status cell to `-` so `parse_roadmap`'s inference logic determines the correct status from the PR column
5. Writes the updated body back via the GitHub API

**Note:** There is no `--status` flag. Status is always inferred from the PR column after update. For full mutation semantics, see [Roadmap Mutation Patterns](roadmap-mutation-patterns.md).

## Status Inference

The parser uses a two-tier status resolution system. For the complete specification, see [Roadmap Status System](roadmap-status-system.md).

**Tier 1 — Explicit status values take priority:**

| Status Column               | Result        |
| --------------------------- | ------------- |
| `done`                      | `done`        |
| `in-progress`/`in_progress` | `in_progress` |
| `pending`                   | `pending`     |
| `blocked`                   | `blocked`     |
| `skipped`                   | `skipped`     |

**Tier 2 — PR-based inference (when status column is `-` or empty):**

| PR Column      | Inferred Status |
| -------------- | --------------- |
| `#XXXX`        | `done`          |
| `plan #XXXX`   | `in_progress`   |
| (empty or `-`) | `pending`       |

**All explicit status values override PR column inference**, not just `blocked` and `skipped`.

## Step ID Format

**Preferred**: Plain numbers — `1.1`, `1.2`, `2.1`, `3.1`

**Deprecated**: Letter format — `1A.1`, `1B.2`, `2A.1`

The parser accepts both formats but emits a validation warning for letter-format IDs. All templates now use plain numbers.

## Next Step Discovery

`find_next_step()` returns the first step with `pending` status in phase order. This is used by `erk objective check --json-output` to populate the `next_step` field, and by `erk objective next-plan` to determine which step to implement next.

## Implementation Reference

- Shared parser: `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`
- Check command: `src/erk/cli/commands/objective/check_cmd.py`
- Update command: `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`

## Related Documentation

- [Roadmap Parser API Reference](roadmap-parser-api.md) — Code-level API for parser functions and data types
- [Roadmap Status System](roadmap-status-system.md) — Complete two-tier status resolution specification
- [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) — Surgical vs full-body update decisions
- [objective-roadmap-check](objective-roadmap-check.md) — Detailed check command reference
- [Objectives Index](index.md) — Package overview and key types
- [Objective Format Reference](../../../.claude/skills/objective/references/format.md) — Templates and examples
- [Glossary: Objectives System](../glossary.md#objectives-system) — Terminology definitions
