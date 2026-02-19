---
title: Schema V3 Migration
read_when:
  - "working with plan metadata YAML keys"
  - "modifying roadmap parsing or rendering"
  - "encountering steps vs nodes naming in plan metadata"
tripwires:
  - action: "using 'steps' instead of 'nodes' in new plan metadata code"
    warning: "Schema v3 uses 'nodes' (not 'steps'). The parser accepts both for backward compatibility but the renderer always emits v3. See schema-v3-migration.md."
---

# Schema V3 Migration

Plan metadata YAML keys were renamed from v2 to v3.

## What Changed

| v2 Key             | v3 Key             |
| ------------------ | ------------------ |
| `steps`            | `nodes`            |
| `completed_steps`  | `completed_nodes`  |
| `total_steps`      | `total_nodes`      |
| `step_description` | `node_description` |

## Backward Compatibility

### Roadmap Parser

`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` (lines 76-87) accepts both v2 and v3 keys:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py, validate_roadmap_frontmatter -->

See `validate_roadmap_frontmatter()` in `roadmap.py` — accepts both v2 `steps` and v3 `nodes` keys for backward compatibility.

Supported schema versions: `"2"` and `"3"`.

### Metadata Blocks

`packages/erk-shared/src/erk_shared/gateway/github/metadata_blocks.py` (lines 54-58) normalizes legacy field names during validation:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata_blocks.py -->

See field normalization in `metadata_blocks.py` — renames legacy `completed_steps`/`total_steps` to v3 `completed_nodes`/`total_nodes`.

### Renderer

The renderer always emits v3 format (`"nodes"`, schema version `"3"`), never v2.

## Convention

New code should always use v3 keys (`nodes`, `completed_nodes`, `total_nodes`, `node_description`). The v2 fallback exists only for reading existing metadata.

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Full metadata schema documentation
