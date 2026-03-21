---
title: Multi-Node Plans
read_when:
  - "creating a plan that covers multiple objective nodes"
  - "debugging why only the first node was marked done after landing"
  - "working with node_ids in plan-header metadata"
  - "understanding how landing updates multiple objective nodes"
tripwires:
  - action: "relying on PR body text to determine which nodes a plan covers"
    warning: "PR body parsing for node IDs is the fallback path. Primary source is plan-header metadata `node_ids` field, written during plan creation. Read from metadata first."
  - action: "writing node_ids as a list inside PlanHeaderData"
    warning: "PlanHeaderData stores node_ids as tuple[str, ...] internally. The list↔tuple conversion happens at serialization boundaries. See typed-metadata-pattern.md."
---

# Multi-Node Plans

## Problem

Multi-node PRs (plans covering more than one objective roadmap node) previously only marked the first node as done during landing. Subsequent nodes were not updated.

## Solution

The `node_ids` field in plan-header metadata provides durable storage of which nodes a plan covers. This persists across the full lifecycle: plan creation → implementation → landing.

## Schema

`NODE_IDS` constant in `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py:396`:

```python
NODE_IDS: Literal["node_ids"] = "node_ids"
```

Validation in `PlanHeaderSchema.validate()` (line 684):

- Must be a list or null
- All items must be strings

Field in `PlanHeaderData` (line 87): `node_ids: tuple[str, ...] | None = None`

## Auto-Discovery Flow

`objective_apply_landed_update()` at `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py:249`:

```python
if node_ids:
    matched_steps = list(node_ids)      # Caller-provided (highest priority)
elif plan_result.node_ids:
    matched_steps = list(plan_result.node_ids)  # From plan metadata (primary)
```

Priority order:

1. Caller-provided `node_ids` (from CLI argument)
2. Plan metadata `node_ids` (read from plan-header block)
3. PR body reference parsing (fallback, not shown)

## Lifecycle

1. **Plan creation**: `node_ids` written to plan-header during `erk exec plan-save`
2. **Implementation**: Metadata preserved across PR body updates
3. **Landing**: `objective-apply-landed-update` reads `node_ids` from plan metadata → marks all nodes done

## Related Documentation

- [Typed Metadata Pattern](../architecture/typed-metadata-pattern.md) — How PlanHeaderData handles node_ids serialization
- [Planned PR Backend](planned-pr-backend.md) — How plan metadata is stored and updated
