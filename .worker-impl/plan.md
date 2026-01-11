# Plan: Add tripwires-review as a Capability

## Summary

Add `tripwires-review` as an installable capability via `erk init capability add tripwires-review`.

## Files to Create

### `src/erk/core/capabilities/tripwires_review.py`

Create a new capability class following the `DignifiedReviewCapability` pattern:

```python
class TripwiresReviewCapability(Capability):
    name = "tripwires-review"
    description = "GitHub Action for tripwire code review"
    scope = "project"

    artifacts:
    - .github/workflows/tripwires-review.yml
    - .github/prompts/tripwires-review.md

    install:
    - Copy workflow file from bundled .github/
    - Copy prompt file from bundled .github/
    - Copy setup-claude-code action if not already installed
```

## Files to Modify

### `src/erk/core/capabilities/registry.py`

- Import `TripwiresReviewCapability`
- Add `TripwiresReviewCapability()` to `_all_capabilities()` tuple

## Tests

Create `tests/core/capabilities/test_tripwires_review.py`:
- Test `is_installed()` returns False when workflow doesn't exist
- Test `is_installed()` returns True when workflow exists
- Test `install()` copies workflow, prompt, and setup-claude-code action
- Test `install()` skips action if already installed

## Verification

1. Run `erk init capability list` - should show `tripwires-review`
2. Run `erk init capability check tripwires-review` - should show installation status
3. Run `erk init capability add tripwires-review` - should install workflow + prompt
4. Verify files exist at `.github/workflows/tripwires-review.yml` and `.github/prompts/tripwires-review.md`