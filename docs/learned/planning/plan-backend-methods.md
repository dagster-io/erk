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
  - action: "creating a fake PlanBackend for testing application code"
    warning: "Fake backends validate the ABC contract only. To test code that uses a backend, inject fake gateways into the real backend. See the Testing Pattern section."
---

# PlanBackend ABC Methods

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/backend.py, PlanBackend -->

PlanBackend extends PlanStore with write operations for plan management. It follows the Backend ABC pattern (3-place: abc, real, fake) — see [Gateway vs Backend](../architecture/gateway-vs-backend.md).

## Architecture: Schema v2

GitHub plan storage separates metadata from content:

- **Issue body**: Contains `plan-header` metadata block (YAML in HTML comments)
- **First comment**: Contains plan content (the actual plan markdown)

This separation exists so metadata updates (e.g., recording a dispatch timestamp) don't require touching plan content, and vice versa. This avoids merge conflicts when multiple operations target the same plan concurrently.

## PlanStore (Deprecated)

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/store.py, PlanStore -->

PlanStore is a **deprecated** read-only subset of PlanBackend. It is retained only for backward compatibility with existing type annotations. New code should use PlanBackend for full read/write access. See `PlanStore` in `packages/erk-shared/src/erk_shared/plan_store/store.py` for the deprecation notice.

## Read Operations (from PlanStore)

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/backend.py, PlanBackend -->

| Method                 | Purpose                   | Returns                  |
| ---------------------- | ------------------------- | ------------------------ |
| `get_plan()`           | Fetch plan by ID          | `Plan \| PlanNotFound`   |
| `list_plans()`         | Query plans by criteria   | `list[Plan]`             |
| `get_provider_name()`  | Get provider identifier   | `str`                    |
| `close_plan()`         | Close a plan by ID        | `None`                   |
| `get_metadata_field()` | Get single metadata value | `object \| PlanNotFound` |

### get_metadata_field() Details

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.get_metadata_field -->

This method exists separately from `get_plan()` to avoid the cost of fetching plan content when only a single metadata field is needed. Plan content lives in a separate comment and requires an additional API call; `get_metadata_field()` reads only the issue body's `plan-header` block.

Returns `None` if the field is unset (vs `PlanNotFound` if the plan doesn't exist) — callers must distinguish between "field not set" and "plan not found" using type narrowing on the return value.

## Write Operations (from PlanBackend)

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/backend.py, PlanBackend -->

| Method                  | Purpose                            | Key Detail                             |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| `create_plan()`         | Create new plan                    | Creates issue + content comment        |
| `update_metadata()`     | Update metadata fields             | Blocklist of 3 immutable fields        |
| `update_plan_content()` | Update plan body                   | Two-tier comment lookup                |
| `add_comment()`         | Add comment to plan                | Returns comment ID                     |
| `post_event()`          | Metadata update + optional comment | Combines add_comment + update_metadata |

### update_metadata() Details

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.update_metadata -->

Uses a **blocklist** of 3 immutable fields (`schema_version`, `created_at`, `created_by`) rather than a whitelist. This design means new metadata fields are allowed by default — adding a new field to `PlanHeaderSchema` automatically makes it settable without updating the write path. Only fields that must never change after creation are protected.

Validates via `PlanHeaderSchema` after merging, so unknown fields are still caught by schema validation.

### update_plan_content() Details

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.update_plan_content -->

Uses **two-tier comment lookup** because `plan_comment_id` was added to the metadata schema after plans already existed. Older plans lack this field, so the fallback to the first comment ensures backward compatibility. The two-tier approach:

1. Check `plan_comment_id` from plan-header metadata (direct lookup — O(1) API call)
2. Fall back to fetching all comments and using the first one (list lookup — slower)

New plans always have `plan_comment_id` set, so the fallback only triggers for legacy plans.

### post_event() Details

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/github.py, GitHubPlanStore.post_event -->

Convenience method combining a comment and metadata update in a single call. Comment is posted first (if provided), then metadata is updated. This ordering ensures the comment exists before metadata references it (e.g., if metadata stores a `plan_comment_id`).

## FakeLinearPlanBackend

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/fake_linear.py, FakeLinearPlanBackend -->

The fake implementation at `plan_store/fake_linear.py` validates that the ABC contract works across fundamentally different providers (UUID-based IDs, 5-state workflow, single assignee, metadata in custom_fields). It uses **frozen dataclass replacement** for updates — creating new `LinearIssue` instances rather than mutating in place.

### Testing Pattern

Fake backends exist **only** to validate the ABC contract works across different providers. They are NOT for testing application code that uses a backend.

To test code that uses a PlanBackend, inject fake **gateways** into the **real** backend:

```python
# CORRECT: Real backend with fake gateway
fake_issues = FakeGitHubIssues()
backend = GitHubPlanStore(fake_issues)
result = backend.create_plan(...)
```

```python
# WRONG: Using FakeLinearPlanBackend to test application code
backend = FakeLinearPlanBackend()
my_service = PlanService(backend)  # Don't do this
```

See `PlanBackend` module docstring in `packages/erk-shared/src/erk_shared/plan_store/backend.py` for the canonical example.

## Related Documentation

- [Gateway vs Backend ABC Pattern](../architecture/gateway-vs-backend.md) — 3-place vs 5-place distinction
- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — For gateway (not backend) ABCs
