# Remove Duplicate `ensure()` via Explicit Protocol Inheritance

## Context

Five `NonIdealState` classes in `non_ideal_state.py` each define an identical `ensure()` method:

```python
def ensure(self) -> NoReturn:
    raise NonIdealStateError(self)
```

The `NonIdealState` Protocol already has this as a **concrete method body**. When a class explicitly inherits from a Protocol (rather than just structurally satisfying it), it inherits that concrete implementation. The fix is to add `(NonIdealState)` to each class signature and delete the 5 duplicate `ensure()` methods.

## File to Modify

`packages/erk-shared/src/erk_shared/non_ideal_state.py`

## Changes (5 classes, same pattern each)

For each of these classes: `BranchDetectionFailed`, `NoPRForBranch`, `PRNotFoundError`, `GitHubAPIFailed`, `SessionNotFound`:

1. Change `@dataclass(frozen=True)\nclass Foo:` → `@dataclass(frozen=True)\nclass Foo(NonIdealState):`
2. Delete the 2-line `ensure()` method body

No other files need to change. `NonIdealState` is defined above these classes in the same file, so there's no forward reference issue.

## No Behavior Change

- `ensure()` still raises `NonIdealStateError(self)` — inherited from Protocol
- `isinstance(obj, NonIdealState)` still returns `True` for all 5 classes (explicit inheritance works the same as structural for `@runtime_checkable`)

## Verification

Run the erk-shared unit tests to confirm no regressions:

```
pytest packages/erk-shared/tests/ -x
```
