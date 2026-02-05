# Plan: Allow Assert for Type Narrowing in Dignified Python

## Context

PR #6723 has an automated review comment flagging `assert result.metadata is not None` (line 124 of `objective_roadmap_frontmatter.py`) as a LBYL violation. This is a **false positive** — the preceding `if not result.is_valid: return None` check already guarantees `metadata is not None` (since `is_valid` is `return self.metadata is not None`). The assert is purely for type narrowing, not control flow.

Three docs need updating to recognize this pattern, plus the PR thread should be resolved as a false positive.

## Changes

### 1. `.claude/skills/dignified-python/dignified-python-core.md` (line ~73)

Add a new subsection under "When Exceptions ARE Acceptable" (or after it, before Path Operations) documenting that `assert` for type narrowing is acceptable:

```markdown
### Assert for Type Narrowing

`assert` is acceptable when used **solely to narrow types** after a guard check has already established the invariant:

```python
# CORRECT: assert for type narrowing after guard check
if not result.is_valid:
    return None
# is_valid guarantees metadata is not None, assert narrows the type
assert result.metadata is not None
process(result.metadata)

# WRONG: assert as control flow (no prior guard)
assert result.metadata is not None  # This IS control flow
process(result.metadata)
```

The key distinction: if removing the assert would cause a runtime error, it's control flow (WRONG). If removing it would only lose type information, it's type narrowing (ACCEPTABLE).
```

### 2. `.claude/skills/dignified-python/references/typing-advanced.md`

Generalize the "immediately after a type guard" section (currently scoped to `cast()`) to cover assert-for-type-narrowing broadly. Add a new section after the `cast()` section:

```markdown
## Assert for Type Narrowing

Beyond `cast()`, bare `assert` statements are acceptable for type narrowing when:

1. A prior guard check already establishes the invariant
2. The assert is redundant at runtime but informs the type checker

```python
# CORRECT: Guard establishes invariant, assert narrows type
if not result.is_valid:
    return None
assert result.metadata is not None  # Type narrowing only
```

This is NOT a LBYL violation — removing the assert wouldn't cause a runtime error, it would only lose type information.
```

### 3. `.github/reviews/dignified-python.md` (line ~85-86)

Add an exception to the LBYL rule in the reviewer instructions:

In the "CRITICAL: Check for exceptions before flagging violations" section, add:

```
- **LBYL rule**: `assert` used purely for type narrowing after a guard check is NOT a violation (e.g., `assert x is not None` after `if not is_valid: return None` where `is_valid` checks `x is not None`)
```

### 4. Resolve PR thread as false positive

Resolve thread `PRRT_kwDOPxC3hc5swhyA` with a comment explaining this is a false positive — the assert is type narrowing after an already-verified invariant, not control flow.

## Verification

1. Run `make py-fast-ci` (docs changes only, should pass trivially)
2. Resolve the thread on PR #6723
3. Quick-submit the changes