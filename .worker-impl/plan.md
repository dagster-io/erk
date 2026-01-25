# Plan: Remove tripwire_candidates module

## Summary

Delete the `tripwire_candidates.py` module and its tests. This module parsed tripwire candidates from learn plan markdown but has no active consumers.

## Files to Delete

1. `packages/erk-shared/src/erk_shared/learn/tripwire_candidates.py`
2. `tests/unit/learn/test_tripwire_candidates.py`

## Verification

Run tests scoped to the learn package:
```bash
uv run pytest tests/unit/learn/ -v
```