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
