---
title: Mixed Exception/Union Pattern (Deprecated)
last_audited: "2026-02-07 21:45 PT"
audit_result: edited
read_when:
  - "considering mixing discriminated unions with exceptions in gateway methods"
  - "designing operations with both expected failures and cleanup steps"
  - "reviewing historical gateway error handling experiments"
tripwires:
  - action: "mixing discriminated unions with exception-based cleanup in a single method"
    warning: "This pattern was tried in PR #6347 and reverted in PR #6375. Message-only discriminated unions with no domain-meaningful variants add complexity without value. Use exceptions for all error cases, or use discriminated unions with meaningful variants throughout. Document why in the PR."
---

# Mixed Exception/Union Pattern (Deprecated)

**Status**: This pattern was implemented and then reverted. It is **not currently used** in erk.

This document explains WHY the mixed exception/union pattern was tried and WHY it was abandoned, to prevent future attempts at the same failed approach.

## The Attempted Pattern

In January 2026, we experimented with mixing error handling strategies in a single gateway method:

- **Main operation** returns discriminated union (`WorktreeRemoved | WorktreeRemoveError`)
- **Cleanup operation** raises exception (`RuntimeError`)

The hypothesis was that this distinguished between "expected failures" (main operation) and "corrupted state" (cleanup failures).

## Why It Was Tried

<!-- Source: PR #6347 - Phase 5 Convert remove_worktree to Discriminated Union -->

The `remove_worktree` method had two distinct failure modes:

1. **Expected failures**: Worktree doesn't exist, is in use, permission denied → could be handled gracefully
2. **Cleanup failures**: `git worktree prune` fails → indicates repository corruption

The discriminated union conversion aimed to make expected failures explicit while keeping cleanup failures exceptional.

See PR #6347 for the full implementation attempt.

## Why It Was Reverted

<!-- Source: PR #6375 - Convert Worktree add/remove back to exceptions -->

The pattern was reverted after 1 day because:

### 1. No Domain-Meaningful Variants

The discriminated union types (`WorktreeRemoved`, `WorktreeRemoveError`) were **structureless message wrappers**:

- No meaningful variant types (like "in use" vs "permission denied")
- Just a single `message: str` field
- Callers couldn't distinguish between error types anyway
- Added boilerplate without adding capability

**The lesson**: Discriminated unions only add value when they have domain-meaningful variants that callers actually distinguish between. Message-only wrappers are busywork.

### 2. Exception Boundaries Already Exist

The CLI commands already catch exceptions at natural boundaries (Click command handlers). Moving the try/except from CLI to gateway didn't eliminate exception handling - it just moved it.

**The lesson**: Exception-based error handling works fine when exceptions are caught at architectural boundaries (CLI layer). Don't convert to discriminated unions just to avoid exceptions.

### 3. Mixed Patterns Are Confusing

Having one method return a union for some errors and raise exceptions for others creates cognitive load:

- Callers must remember which errors are in the return type and which are exceptions
- Mixed docstrings are harder to read
- No tooling support for "this method returns X | Y but also raises Z"

**The lesson**: Pick one strategy per method. Mixing strategies within a single operation is an anti-pattern.

## The Current Approach

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py, remove_worktree -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/worktree/real.py, remove_worktree -->

Gateway methods use **exceptions for all failures**. See `remove_worktree` in `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py` — it returns `None` and raises `RuntimeError` on failure. No discriminated union types involved.

CLI commands catch these exceptions at their natural boundaries (Click command handlers), converting them to `click.ClickException` for user-facing output. See callers in `src/erk/cli/commands/wt/delete_cmd.py` and `src/erk/cli/commands/navigation_helpers.py`.

This is simpler, less code, and works well when all callers terminate identically on failure — no caller branches on error content or inspects error structure.

## When Discriminated Unions DO Work

Discriminated unions are valuable when:

1. **Multiple domain-meaningful variants** exist that callers distinguish between
   - Example: `PRDetails | PRNotFound` — callers check `isinstance(result, PRNotFound)` and inspect `result.branch` or `result.pr_number`
2. **Type narrowing provides value** at the call site
   - Example: `if isinstance(result, PRNotFound): handle_missing(result.branch)`
3. **The variants have different fields** that encode domain information
   - Not just `message: str` wrappers

See `docs/learned/architecture/discriminated-union-error-handling.md` for current discriminated union patterns.

## Decision Framework

When designing gateway error handling:

| Situation                                         | Use                    | Reason                               |
| ------------------------------------------------- | ---------------------- | ------------------------------------ |
| Single failure mode with message                  | Exception              | No variants to distinguish           |
| Multiple failure modes, callers don't distinguish | Exception              | Type system overhead without benefit |
| Multiple failure modes, callers DO distinguish    | Discriminated union    | Type narrowing adds value            |
| Cleanup operation in same method                  | Same as main operation | Don't mix strategies                 |

**Never mix exceptions and discriminated unions in a single method signature.** Choose one strategy for all error cases.

## Related Documentation

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - When and how to use discriminated unions
- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-place implementation checklist
- [LBYL Gateway Pattern](lbyl-gateway-pattern.md) - LBYL principles for gateway design
