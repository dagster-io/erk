# Plan: Fix false positive review for ternary context managers

## Context

The dignified-code-simplifier review (run by Haiku) is incorrectly suggesting to extract conditional/ternary context managers into intermediate variables. This is a false positive — context managers should stay inline in `with` statements because extracting them to variables obscures the `__enter__`/`__exit__` lifecycle.

The root cause is the absence of explicit guidance. Haiku over-applies the general "choose clarity over brevity" rule to ternary `with` expressions.

## Changes

### 1. `.claude/skills/dignified-code-simplifier/SKILL.md` (line ~32)

Add a bullet in the "Enhance Clarity" section (item 3) after the ternary operator guidance:

```
- Conditional context managers (ternary in `with` statements) should stay inline — do NOT suggest extracting them to intermediate variables. Context managers belong in `with` statements where the lifecycle is explicit. Example: `with (cm_a if condition else nullcontext()):` is correct.
```

### 2. `.agents/skills/dignified-python/dignified-python-core.md` (if context manager guidance exists there)

Add equivalent guidance about keeping context managers inline in `with` statements.

## Verification

- Run the dignified-code-simplifier review against the current PR diff and confirm it no longer flags ternary context managers
