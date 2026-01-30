---
title: Roadmap Parser
read_when:
  - "understanding how roadmap steps are parsed"
  - "working with objective roadmap check or update commands"
  - "debugging roadmap parsing issues"
  - "using erk exec objective-roadmap-check or objective-roadmap-update"
tripwires:
  - action: "implementing roadmap parsing functionality"
    warning: "The parser is regex-based, not LLM-based. Do not reference LLM inference."
  - action: "creating or modifying roadmap step IDs"
    warning: "Step IDs should use plain numbers (1.1, 2.1), not letter format (1A.1, 1B.1)."
---

# Roadmap Parser

This document describes how erk parses and mutates objective roadmap tables using regex-based parsing.

## Overview

Erk uses deterministic regex parsing to extract structured data from objective roadmap markdown tables. Two exec commands expose this functionality:

- **`objective-roadmap-check`** — parse and validate a roadmap, returning structured JSON
- **`objective-roadmap-update`** — mutate a specific step's status or PR column

Both commands share the parser in `objective_roadmap_shared.py`.

## Check Command

```bash
erk exec objective-roadmap-check <OBJECTIVE_NUMBER>
```

Fetches the objective issue body from GitHub, parses all roadmap tables, and returns JSON:

```json
{
  "success": true,
  "issue_number": 6295,
  "title": "Objective: ...",
  "phases": [
    {
      "number": 1,
      "name": "Phase Name",
      "steps": [
        { "id": "1.1", "description": "...", "status": "done", "pr": "#123" },
        { "id": "1.2", "description": "...", "status": "pending", "pr": null }
      ]
    }
  ],
  "summary": {
    "total_steps": 10,
    "pending": 3,
    "done": 6,
    "in_progress": 1,
    "blocked": 0,
    "skipped": 0
  },
  "next_step": { "id": "1.2", "description": "...", "phase": "Phase Name" },
  "validation_errors": []
}
```

### Parsing Rules

1. **Phase headers**: Matches `### Phase N: Name` (with optional `(N PR)` suffix)
2. **Table structure**: Expects `| Step | Description | Status | PR |` header with separator
3. **Row extraction**: Each `| id | desc | status | pr |` row becomes a `RoadmapStep`

### Validation

The parser emits warnings (not errors) for:

- Missing phase headers
- Missing or malformed table structure
- Letter-format step IDs (e.g., `1A.1` — prefer `1.1`)

## Update Command

```bash
erk exec objective-roadmap-update <OBJECTIVE_NUMBER> --step <STEP_ID> [--status <STATUS>] [--pr <PR_REF>]
```

| Flag       | Required | Example             | Description       |
| ---------- | -------- | ------------------- | ----------------- |
| `--step`   | yes      | `2.1`               | Step ID to update |
| `--status` | no       | `done`, `blocked`   | New status value  |
| `--pr`     | no       | `#123`, `plan #456` | New PR reference  |

The command:

1. Fetches the issue body
2. Regex-finds the target row by step ID
3. Edits the status and/or PR columns in place
4. Writes the updated body back via the GitHub API
5. Re-runs check to validate the result

## Status Inference

The parser infers step status from both columns:

| Status Column | PR Column      | Inferred Status |
| ------------- | -------------- | --------------- |
| `blocked`     | (any)          | `blocked`       |
| `skipped`     | (any)          | `skipped`       |
| (other)       | `#XXXX`        | `done`          |
| (other)       | `plan #XXXX`   | `in_progress`   |
| (other)       | (empty or `-`) | `pending`       |

**Status column takes priority** — `blocked` and `skipped` override PR column inference.

## Step ID Format

**Preferred**: Plain numbers — `1.1`, `1.2`, `2.1`, `3.1`

**Deprecated**: Letter format — `1A.1`, `1B.2`, `2A.1`

The parser accepts both formats but emits a validation warning for letter-format IDs. All templates now use plain numbers.

## Next Step Discovery

`find_next_step()` returns the first step with `pending` status in phase order. This is used by `objective-next-plan` to determine which step to implement next.

## Implementation Reference

- Shared parser: `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py`
- Check command: `src/erk/cli/commands/exec/scripts/objective_roadmap_check.py`
- Update command: `src/erk/cli/commands/exec/scripts/objective_roadmap_update.py`

## Related Documentation

- [Objectives Index](index.md) — Package overview and key types
- [Objective Format Reference](../../../.claude/skills/objective/references/format.md) — Templates and examples
- [Glossary: Objectives System](../glossary.md#objectives-system) — Terminology definitions
