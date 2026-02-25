---
title: Impl-Context API
read_when:
  - "working with .erk/impl-context/ folder"
  - "understanding plan submission staging"
  - "creating or removing impl-context directories"
tripwires:
  - action: "creating .erk/impl-context/ without using create_impl_context()"
    warning: "Use the three-function API in impl_context.py. Manual folder creation skips validation and ref.json generation."
    score: 4
  - action: "removing .erk/impl-context/ during implementation without git rm"
    warning: "Use git rm -rf for committed impl-context (Step 2d of plan-implement). The remove_impl_context() function is for filesystem-only removal."
    score: 3
---

# Impl-Context API

The `.erk/impl-context/` folder is a staging directory committed to the branch during plan submission. Unlike `.impl/` (ephemeral, local, never committed), `.erk/impl-context/` is visible in the draft PR immediately and removed before implementation begins.

## Three-Function API

**Location:** `packages/erk-shared/src/erk_shared/impl_context.py`

### create_impl_context()

Creates `.erk/impl-context/` with `plan.md` and `ref.json`.

```python
create_impl_context(
    plan_content="# Plan: ...",
    plan_id="42",
    url="https://github.com/owner/repo/pull/42",
    repo_root=Path("/path/to/repo"),
    provider="github-draft-pr",
    objective_id=None,
    now_iso="2026-01-15T10:00:00+00:00",  # Time abstraction
)
```

- Accepts `now_iso` parameter for time abstraction (testability)
- Raises `FileExistsError` if folder already exists (LBYL)
- Raises `ValueError` if `repo_root` doesn't exist or isn't a directory
- No README.md — this folder is automation-only, not human-facing

### remove_impl_context()

Removes `.erk/impl-context/` folder and all contents.

- Raises `FileNotFoundError` if folder doesn't exist
- Raises `ValueError` if `repo_root` doesn't exist

### impl_context_exists()

Returns `bool`. Handles missing `repo_root` gracefully (returns `False`).

## Folder Structure

```
.erk/impl-context/
├── plan.md      # Full plan content from GitHub issue
└── ref.json     # Plan reference metadata (provider, plan_id, url, etc.)
```

## Two-Phase Deferred Cleanup

The cleanup of `.erk/impl-context/` happens in two phases:

1. **Setup phase** (`plan-save`): Filesystem copy — `create_impl_context()` creates the folder, then git commits it to the branch
2. **Implementation phase** (`plan-implement` Step 2d): `git rm -rf .erk/impl-context/` removes it from the branch before implementation begins

This deferred cleanup ensures the plan is visible in the draft PR during the review period but doesn't interfere with implementation.

## Cleanup-and-Recreate Guard

In `submit.py`, the pattern cleans up any previous impl-context before creating a fresh one (e.g., from a prior failed submission):

```python
if impl_context_exists(repo_root):
    remove_impl_context(repo_root)
create_impl_context(...)
```

## Related Documentation

- [Impl Folder Lifecycle](impl-folder-lifecycle.md) — Full lifecycle of .impl/ and .erk/impl-context/ folders
- [Plan Ref Architecture](plan-ref-architecture.md) — ref.json schema and migration
