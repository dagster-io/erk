# Clarify Default Parameter Rule in dignified-python Skill

## Problem

The CI bot (GitHub Actions) incorrectly flagged this code as a violation:
```python
user_confirm("Close the PR?", default=True)
```

This is a **false positive**. The rule "Default Parameter Values Are Dangerous" applies to **function definitions** like:
```python
def foo(bar: bool = False):  # BAD - default parameter value in DEFINITION
```

NOT to **function calls** where you're passing a named argument:
```python
foo(bar=True)  # FINE - just passing an argument to a function
```

The confusion arose because the argument happens to be named `default`, which triggered a naive pattern match.

## Fix

Add a clarification to the "Default Parameter Values Are Dangerous" section in `dignified-python-core.md` to explicitly distinguish between:
1. **Function definitions** (where the rule applies)
2. **Function calls** (where passing `default=...` as an argument is fine)

## Files to Modify

- `.claude/skills/dignified-python/dignified-python-core.md`: Lines 882-933

## Implementation

Add a clarification box after the section title explaining the scope of the rule:

```markdown
> **Scope:** This rule applies to **function definitions** (`def foo(bar: bool = False)`),
> NOT to **function calls** where you pass an argument named `default` (e.g.,
> `click.confirm(default=True)`). Passing `default=True` to a function that accepts
> a `default` parameter is perfectly valid—you're not creating a default parameter value,
> you're explicitly providing a value.
```