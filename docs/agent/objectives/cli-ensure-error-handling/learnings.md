# Learnings

Discoveries that inform future work on this objective. Add entries as you learn things.

---

## Patterns

### Type narrowing is the key value-add

The biggest benefit of Ensure methods isn't just consistent styling - it's returning narrowed types. `Ensure.not_none(x, msg)` returns `T` from `T | None`, eliminating downstream None checks.

**Implication**: When adding new Ensure methods, always consider if they can return a narrowed type.

### Domain-specific vs generic

- Use `Ensure.invariant(condition, msg)` for one-off checks
- Create domain-specific methods when a pattern appears 2+ times with similar messaging
- Domain methods encode the error message, reducing caller boilerplate

### Exception re-raising needs care

Patterns like `raise SystemExit(1) from e` preserve exception chains. When converting these:
- The Ensure pattern doesn't naturally support `from e`
- Consider whether chain preservation matters for the specific error
- May need a different approach for exception wrapping

---

## Edge Cases

### SystemExit(0) is not an error

Some code uses `raise SystemExit(0)` for successful early termination. This is intentional and not a conversion target.

### Shell integration is special

`src/erk/cli/commands/shell_integration.py` forwards exit codes from subprocess results. This is correct behavior, not an error pattern.

### Helpful error messages with dynamic context

Some error patterns gather additional context before displaying the error (e.g., `goto_cmd.py` lists available worktrees when a worktree isn't found, adds conditional hints). These don't fit Ensure well because:
- The error message includes runtime-computed lists
- There's conditional logic for hints based on input shape
- The value isn't just "missing" - there's discovery and suggestion

**Keep manual handling for these** unless a domain-specific Ensure method encapsulates the entire pattern.

### Check commands have legitimate exit codes

Commands like `pr check` use `SystemExit(0)` for "all checks pass" and `SystemExit(1)` for "checks failed". This isn't error handling - it's exit status semantics. Leave these as-is.

---

## Open Questions

- Should `ensure-conversion-tasks.md` be migrated into this folder or kept alongside the Ensure implementation?
- Are there patterns that genuinely shouldn't use Ensure? Document them here as they're discovered.
