---
title: Plan Schema Reference
read_when:
  - "understanding plan issue structure"
  - "debugging plan validation errors"
  - "working with plan-header or plan-body blocks"
last_audited: "2026-02-03 04:00 PT"
audit_result: edited
---

# Plan Schema Reference

## Two-Part Structure

Plan issues use a two-part structure optimized for GitHub API performance:

| Location      | Block Key     | Purpose                                  |
| ------------- | ------------- | ---------------------------------------- |
| Issue body    | `plan-header` | Compact metadata for fast querying       |
| First comment | `plan-body`   | Full plan content in collapsible details |

This separation means metadata can be queried from the issue body without fetching comments (which is a separate API call).

## Source of Truth

- **Field definitions:** `PlanHeaderSchema` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` — contains all required/optional fields with validation
- **Block format:** See [Metadata Blocks Reference](../architecture/metadata-blocks.md)
- **Plan header operations:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`
- **Validation:** Run `erk plan check <issue-number>` (see `src/erk/cli/commands/plan/check_cmd.py`)

## Related Documentation

- [Metadata Blocks Reference](../architecture/metadata-blocks.md) - Block format and parsing API
