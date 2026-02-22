---
title: Exception Logging Patterns
read_when:
  - "deciding between logger.debug and UserFacingCliError for error handling"
  - "implementing best-effort cleanup alongside primary operations"
  - "writing error handling for multi-step CLI operations"
---

# Exception Logging Patterns

Erk CLI commands use an asymmetric error handling pattern that distinguishes primary operations from secondary cleanup.

## The Pattern

<!-- Source: src/erk/cli/commands/admin.py, gh_actions_api_key -->

**Primary operations** raise `UserFacingCliError` on failure — these are the actions the user explicitly requested.

See `gh_actions_api_key()` in `src/erk/cli/commands/admin.py` for the canonical example: both `set_secret` and `delete_secret` raise `UserFacingCliError` on `RuntimeError`.

**Secondary operations** use `logger.debug()` for failures — these are best-effort cleanup that shouldn't block the primary action. This is a conceptual pattern for cases where a non-critical side-effect (e.g., removing a stale cache entry) should not prevent the primary operation from succeeding:

```python
# CONCEPTUAL EXAMPLE — illustrates the pattern, not copied from source
try:
    cleanup_side_effect()
except RuntimeError:
    logger.debug("Side-effect cleanup failed (non-critical)")
```

## When to Use Each

| Operation Type      | Error Handling             | Example                                          |
| ------------------- | -------------------------- | ------------------------------------------------ |
| Primary action      | `raise UserFacingCliError` | Setting the requested secret                     |
| Cleanup/side-effect | `logger.debug()`           | Deleting the "other" secret for mutual exclusion |
| Validation          | `raise UserFacingCliError` | Checking prerequisites before action             |

## Key Principle

The user should see errors for what they asked to do, not for secondary housekeeping that may or may not succeed. A failed cleanup logged at debug level is preferable to a cryptic error message about an operation the user didn't request.

## Code Location

<!-- Source: src/erk/cli/commands/admin.py -->

`src/erk/cli/commands/admin.py` — `gh_actions_api_key()` (lines 137-194) uses `UserFacingCliError` for primary operations (`set_secret`, `delete_secret`).
