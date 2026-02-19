---
title: dash_data.py JSON Schema
read_when:
  - "consuming dash_data.py JSON output"
  - "building external tools that read plan data"
  - "debugging JSON serialization issues"
---

# dash_data.py JSON Schema

The `dash_data.py` exec script emits plan data as JSON via `dataclasses.asdict(PlanRowData)`.

## Current Field Names

- `plan_id` (formerly `issue_number`)
- `plan_url` (formerly `issue_url`)
- `plan_body` (formerly `issue_body`)

See `_serialize_plan_row()` in `src/erk/cli/commands/exec/scripts/dash_data.py`.

## Breaking Changes Policy

Per project policy (see `docs/learned/conventions.md`), erk does not maintain backwards compatibility. External consumers must update when field names change.

## External Consumer Checklist

If consuming dash_data JSON output, check for:

- Field name references in parsing code
- JSON key expectations in tests
- Any caching or persistence that stores field names
