<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2026-02-19T12:44:08.034032+00:00'
created_by: schrockn
plan_comment_id: null
last_dispatched_run_id: '22193195625'
last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAFKtFKaQ
last_dispatched_at: '2026-02-19T17:44:44.372629+00:00'
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
last_remote_impl_run_id: null
last_remote_impl_session_id: null
branch_name: plan-plan-rename-erk-branch-dat-02-19-1244
created_from_session: cf466ca5-9af6-4541-b3b3-ee558d81f304

```

</details>
<!-- /erk:metadata-block:plan-header -->

---

<details>
<summary>original-plan</summary>

# Plan: Rename .erk/branch-data to .erk/impl-context and clean up after implementation

## Context

Draft-PR plans store plan content in `.erk/branch-data/` (committed to the plan branch). This directory persists after implementation completes, leaving stale plan artifacts. Renaming to `.erk/impl-context/` clarifies its lifecycle: created when implementation starts, deleted when done.

## Changes

### 1. Rename `.erk/branch-data/` to `.erk/impl-context/` everywhere

Search for all `branch-data` references and rename to `impl-context`.

### 2. Delete `.erk/impl-context/` after implementation completes

Add cleanup in the implementation finalization path (e.g., `impl-signal ended` or PR submit).

## Verification

- `make fast-ci`
- Confirm `.erk/impl-context/` is created during plan save and deleted after implementation


</details>
---


To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7605 --script)" && erk pr sync --dangerous
```
