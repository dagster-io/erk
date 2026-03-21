---
title: Typed Metadata Pattern (PlanHeaderData)
read_when:
  - "adding a new field to plan-header metadata"
  - "reading or updating plan-header metadata fields"
  - "implementing parse-once/access-many for metadata"
  - "working with PlanHeaderData"
tripwires:
  - action: "using node_ids as a list inside a dataclass"
    warning: "Frozen dataclasses use tuple[str, ...] for node_ids internally. Convert list→tuple in from_dict() and tuple→list in to_dict() at serialization boundaries. See PlanHeaderData:87,113-114,196."
  - action: "hand-constructing a metadata dict instead of using PlanHeaderData.from_dict()"
    warning: "Use PlanHeaderData.from_dict() / from_issue_body() instead of manual dict construction. PlanHeaderData handles all field mapping, defaults, and serialization boundary conversions."
  - action: "calling _update_plan_header() with 12+ lines of boilerplate"
    warning: "_update_plan_header() reduces update functions to 3-5 lines. Pass keyword args for fields to change; the function handles parse, merge, validate, re-render."
---

# Typed Metadata Pattern (PlanHeaderData)

## Pattern

Parse metadata blocks once via `from_dict()` or `from_issue_body()`, access fields as typed attributes, update via `dataclasses.replace()`, and serialize back via `to_dict()` or `to_metadata_block()`.

## Case Study: PlanHeaderData

`PlanHeaderData` at `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header_data.py`:

- **2 required fields**: `created_at`, `created_by`
- **32 optional fields**: all `| None`, defaulting to `None`
- **Frozen dataclass**: immutable; use `dataclasses.replace()` for updates

### Key Methods

| Method                  | Purpose                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| `from_dict(data)`       | Construct from parsed YAML dict; handles `node_ids` list→tuple      |
| `from_issue_body(body)` | Parse plan-header block from full issue body string                 |
| `to_dict()`             | Serialize to dict; injects `schema_version: "2"`, tuple→list        |
| `to_metadata_block()`   | Serialize + validate via `PlanHeaderSchema`, return `MetadataBlock` |
| `to_rendered_block()`   | Serialize, validate, render as markdown string                      |

## Serialization Boundary: node_ids

`node_ids` is stored as `tuple[str, ...]` in the dataclass (frozen dataclass convention) but serialized as `list` at JSON boundaries:

```python
# from_dict: list → tuple
raw_node_ids = data.get(NODE_IDS)
if isinstance(raw_node_ids, list):
    node_ids = tuple(raw_node_ids)

# to_dict: tuple → list
(NODE_IDS, list(self.node_ids) if self.node_ids is not None else None),
```

## Helper Refactoring: \_update_plan_header()

`_update_plan_header()` at `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py:57` reduces boilerplate from ~12 lines to 3-5 lines per update function:

```python
# Before: ~12 lines of parse/merge/validate/render
block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
if block is None:
    raise ValueError("plan-header block not found")
updated_data = dict(block.data)
updated_data[SOME_FIELD] = new_value
schema = PlanHeaderSchema()
schema.validate(updated_data)
new_block = MetadataBlock(key=BlockKeys.PLAN_HEADER, data=updated_data)
return replace_metadata_block_in_body(issue_body, BlockKeys.PLAN_HEADER, render_metadata_block(new_block))

# After: 3-5 lines
return _update_plan_header(issue_body, some_field=new_value, other_field=other_value)
```

## Testing

Round-trip serialization tests verify:

- `from_dict(data.to_dict()) == data`
- All optional fields survive the round-trip as `None`
- `node_ids` converts correctly at both boundaries

Frozen semantics: mutating fields raises `FrozenInstanceError`.

Source: `tests/unit/gateways/github/metadata_blocks/test_plan_header_data.py`

## Related Documentation

- [Multi-Node Plans](../planning/multi-node-plans.md) — Uses `node_ids` field
- [Metadata Field Addition Workflow](../planning/metadata-field-workflow.md) — Adding new fields
