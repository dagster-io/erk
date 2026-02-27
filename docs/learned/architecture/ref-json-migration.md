---
title: Ref JSON Migration
read_when:
  - "working with plan-ref.json or ref.json"
  - "understanding plan reference file formats"
  - "debugging plan reference loading failures"
tripwires:
  - action: "reading plan reference without using read_plan_ref()"
    warning: "Use read_plan_ref() which handles the three-file fallback chain: plan-ref.json → ref.json → issue.json (legacy). Manual JSON parsing skips fallback and field mapping."
    score: 5
---

# Ref JSON Migration

Plan references have evolved through multiple file formats. The `read_plan_ref()` function handles all formats transparently via a fallback chain.

## PlanRef Dataclass

**Location:** `packages/erk-shared/src/erk_shared/impl_folder.py`

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, PlanRef -->

A frozen dataclass with fields: `provider` (PlanProviderType), `plan_id` (str), `url` (str), `created_at` (str, ISO 8601), `synced_at` (str, ISO 8601), `labels` (tuple of str), and `objective_id` (int or None). See `PlanRef` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

## Required Fields Constant

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, _REQUIRED_REF_FIELDS -->

The private `_REQUIRED_REF_FIELDS` tuple in `packages/erk-shared/src/erk_shared/impl_folder.py` defines which fields must be present. Used by `_parse_ref_json()` for LBYL validation before constructing `PlanRef`. See the source file for current fields.

## Fallback Chain in read_plan_ref()

`read_plan_ref(impl_dir)` tries files in this order:

1. **plan-ref.json** — Current format, written by `save_plan_ref()`
2. **ref.json** — Same schema as plan-ref.json, used by `.erk/impl-context/`
3. **issue.json** — Legacy format with different field names (in `.erk/impl-context/`)

The function returns `None` if no valid file is found.

## Shared Parser

Both `plan-ref.json` and `ref.json` use the same parser:

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, _parse_ref_json -->

The shared parser reads JSON, validates all required fields via LBYL (`any(f not in data for f in _REQUIRED_REF_FIELDS)`), and constructs a `PlanRef` or returns `None`. See `_parse_ref_json()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

## Legacy issue.json Field Mapping

The legacy format uses different field names that are automatically mapped:

| issue.json field  | PlanRef field                   |
| ----------------- | ------------------------------- |
| `issue_number`    | `plan_id` (converted to string) |
| `issue_url`       | `url`                           |
| `created_at`      | `created_at`                    |
| `synced_at`       | `synced_at`                     |
| `labels`          | `labels`                        |
| `objective_issue` | `objective_id`                  |

The `provider` is hardcoded to `"github"` for legacy files.

## ref.json Schema

Used by `.erk/impl-context/ref.json`:

```json
{
  "provider": "github-draft-pr",
  "plan_id": "7952",
  "url": "https://github.com/owner/repo/pull/7952",
  "created_at": "2026-02-23T12:43:12.965231",
  "synced_at": "2026-02-23T12:43:12.965231",
  "labels": [],
  "objective_id": null
}
```

## Related Documentation

- [Plan Ref Architecture](plan-ref-architecture.md) — Provider-agnostic plan reference design
- [Impl-Context API](impl-context-api.md) — How ref.json is created in impl-context
