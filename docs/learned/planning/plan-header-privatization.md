---
title: Plan Header Privatization
read_when:
  - "migrating callers of plan_header.py functions"
  - "understanding why plan_header functions are being privatized"
  - "working with PlanBackend metadata operations"
tripwires:
  - action: "importing functions directly from plan_header.py"
    warning: "plan_header.py functions are being privatized. Use PlanBackend methods instead for metadata operations."
---

# Plan Header Privatization

The `plan_header.py` module contains low-level functions for reading/writing plan issue metadata blocks. These are being gradually privatized behind the `PlanBackend` abstraction.

## Migration Status

### Phase 1: PlanBackend Wrapper Methods (Complete)

PlanBackend now provides typed methods for common metadata operations:

- `get_metadata_field()` — read a single field from plan-header
- `update_metadata()` — write fields to plan-header
- `post_event()` — metadata update + optional comment

### Phase 2: Caller Migration (In Progress)

External callers of `plan_header.py` functions should migrate to PlanBackend:

| Old Pattern                                 | New Pattern                                |
| ------------------------------------------- | ------------------------------------------ |
| `extract_plan_header_fields(body)`          | `backend.get_metadata_field(issue, field)` |
| `update_plan_header_in_body(body, updates)` | `backend.update_metadata(issue, updates)`  |

### Phase 3: Privatization (Pending)

Once all external callers migrate, `plan_header.py` functions will be renamed with `_` prefix to signal they are internal to the metadata layer.

## External Callers Inventory

Callers that need migration (grep for `plan_header` imports):

- Exec scripts that read/write plan metadata
- CLI commands that display plan header fields
- Learn workflow scripts

## Related Documentation

- [PlanBackend Migration Guide](plan-backend-migration.md) — Migration patterns and error handling
- [Plan Lifecycle](lifecycle.md) — How metadata flows through the plan lifecycle
