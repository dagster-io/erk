# Fix `erk br co` shell activation in draft PR next steps

## Context

The draft PR "next steps" output shows `erk br co <branch> && erk implement --dangerous`, but this doesn't work because `erk br co` runs in a subprocess — its `chdir()` is invisible to the calling shell. The issue backend already uses the correct pattern: `source "$(erk prepare <num> --script)"`. The draft PR backend needs the same treatment.

See: `docs/learned/cli/shell-activation-pattern.md`

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py` (line 46)

`DraftPRNextSteps.checkout_and_implement` property:

```python
# Before
f"erk br co {self.branch_name} && erk implement --dangerous"

# After
f'source "$(erk br co {self.branch_name} --script)" && erk implement --dangerous'
```

### 2. `.claude/commands/erk/plan-save.md` (line 148)

Update the skill template's draft PR next steps block:

```
# Before
Local: erk br co <branch_name> && erk implement --dangerous

# After
Local: source "$(erk br co <branch_name> --script)" && erk implement --dangerous
```

### 3. `tests/unit/shared/test_next_steps.py` (line 25-27)

Update the assertion in `test_checkout_and_implement_uses_branch_name`:

```python
# Before
assert steps.checkout_and_implement == (
    "erk br co plan-my-feature-02-20 && erk implement --dangerous"
)

# After
assert steps.checkout_and_implement == (
    'source "$(erk br co plan-my-feature-02-20 --script)" && erk implement --dangerous'
)
```

### 4. `packages/erk-shared/tests/unit/output/test_next_steps.py` (line 24)

Update the format output assertion:

```python
# Before
assert "erk br co" in output

# After
assert 'source "$(erk br co' in output
```

## Verification

1. Run: `pytest tests/unit/shared/test_next_steps.py`
2. Run: `pytest packages/erk-shared/tests/unit/output/test_next_steps.py`
