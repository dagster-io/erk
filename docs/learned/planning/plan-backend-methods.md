---
title: PlanBackend ABC Methods
read_when:
  - "adding methods to PlanBackend or PlanStore"
  - "implementing a new plan storage provider"
  - "understanding plan metadata vs plan content storage"
tripwires:
  - action: "updating plan metadata without checking immutable fields"
    warning: "Three fields are immutable (schema_version, created_at, created_by). update_metadata() uses a blocklist, not a whitelist. New metadata fields are allowed by default."
  - action: "adding dry_run or printing implementation to PlanBackend"
    warning: "PlanBackend is a Backend ABC (3-place pattern), not a Gateway. See gateway-vs-backend.md for the distinction."
---

# PlanBackend ABC Methods

PlanBackend extends PlanStore with write operations for plan management. It follows the Backend ABC pattern (3-place: abc, real, fake) — see [Gateway vs Backend](../architecture/gateway-vs-backend.md).

## Architecture: Schema v2/v3

GitHub plan storage separates metadata from content:

- **Issue body**: Contains `plan-header` metadata block (YAML in HTML comments)
- **First comment**: Contains plan content (the actual plan markdown)

This separation allows metadata updates without touching plan content and vice versa.

## Read Operations (from PlanStore)

| Method                 | Purpose                   | Returns                  |
| ---------------------- | ------------------------- | ------------------------ |
| `get_plan()`           | Fetch plan by ID          | `Plan \| PlanNotFound`   |
| `list_plans()`         | Query plans by criteria   | `list[Plan]`             |
| `get_provider_name()`  | Get provider identifier   | `str`                    |
| `get_metadata_field()` | Get single metadata value | `object \| PlanNotFound` |

### get_metadata_field() Details

Reads a single field from the `plan-header` metadata block. Uses `find_metadata_block()` to parse the issue body. Returns `None` if the field is unset (vs `PlanNotFound` if the plan doesn't exist).

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.get_metadata_field -->

**GitHubPlanStore implementation**: See `GitHubPlanStore.get_metadata_field()` in `packages/erk-shared/src/erk_shared/plan_store/github.py`. Fetches issue, parses plan-header block, returns `block.data.get(field_name)`.

## Write Operations (from PlanBackend)

| Method                  | Purpose                            | Key Detail                             |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| `create_plan()`         | Create new plan                    | Creates issue + content comment        |
| `update_metadata()`     | Update metadata fields             | Blocklist of 3 immutable fields        |
| `update_plan_content()` | Update plan body                   | Two-tier comment lookup                |
| `add_comment()`         | Add comment to plan                | Returns comment ID                     |
| `post_event()`          | Metadata update + optional comment | Combines add_comment + update_metadata |

### update_metadata() Details

Updates plan-header metadata in the issue body. Uses a **blocklist** of 3 immutable fields (`schema_version`, `created_at`, `created_by`) rather than a whitelist. Any field not in the blocklist can be updated. Validates via `PlanHeaderSchema` after merging.

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.update_metadata -->

**GitHubPlanStore implementation**: See `GitHubPlanStore.update_metadata()` in `packages/erk-shared/src/erk_shared/plan_store/github.py`. Fetches issue, parses plan-header block, merges new fields (skipping immutable), validates, re-renders block, updates issue body.

### update_plan_content() Details

Updates the plan content in the first comment. Uses **two-tier lookup**: first checks `plan_comment_id` from metadata, then falls back to the first comment on the issue.

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.update_plan_content -->

**GitHubPlanStore implementation**: See `GitHubPlanStore.update_plan_content()` in `packages/erk-shared/src/erk_shared/plan_store/github.py`. Extracts `plan_comment_id` from plan-header. If found, updates that comment directly. Otherwise, fetches all comments and updates the first one.

### post_event() Details

Convenience method combining a comment and metadata update in a single call. Comment is posted first (if provided), then metadata is updated. This ordering ensures the comment exists before metadata references it.

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.post_event -->

**GitHubPlanStore implementation**: See `GitHubPlanStore.post_event()` in `packages/erk-shared/src/erk_shared/plan_store/github.py`. Calls `add_comment()` then `update_metadata()` sequentially.

## FakeLinearPlanBackend Pattern

The fake implementation at `plan_store/fake_linear.py` validates that the ABC contract works across fundamentally different providers. It uses **immutable update semantics** — creating new `LinearIssue` instances via constructor calls rather than mutating in place.

## Related Documentation

- [Gateway vs Backend ABC Pattern](../architecture/gateway-vs-backend.md) — 3-place vs 5-place distinction
- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — For gateway (not backend) ABCs
