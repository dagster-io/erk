---
title: Code Review Filtering
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
read_when:
  - debugging false positives in code review
  - understanding keyword-only parameter exceptions
  - working with ABC/Protocol method validation
tripwires:
  - action: "flagging 5+ parameter violations in code review"
    warning: "Before flagging, verify NO exception applies (ABC/Protocol/Click)"
---

# Code Review Filtering

## Why Exception Filtering Matters

Code reviews enforce dignified-python patterns, but certain structural constraints make some rules impossible to follow. The keyword-only parameter rule (5+ parameters must use `*` separator) exists to improve call-site readability, but breaks down when signatures are constrained by external contracts.

**The core tension**: We want readable call sites in application code, but interface definitions (ABC/Protocol) and framework callbacks (Click) have different priorities. Interface definitions optimize for contract clarity, not call-site readability. Framework callbacks follow the framework's injection rules, not our preferences.

Exception filtering lets the review system distinguish "can't follow the rule due to constraints" from "chose not to follow the rule."

## Exception Categories and Rationale

<!-- Source: .erk/reviews/dignified-python.md -->
<!-- Source: .claude/skills/dignified-python/references/api-design.md -->

### ABC and Protocol Methods: Exempt

ABC and Protocol methods define contracts — adding `*` forces all implementations to match, even when simplified implementations have fewer parameters. This creates a refactoring trap.

### Click Command Callbacks: Exempt

Click injects parameters positionally based on decorator order. Keyword-only parameters after `*` break framework injection.

### Context Objects: Allowed as First Positional

Context objects (`ctx`, `self`, `cls`) can remain positional as the first parameter, followed by `*` for data parameters.

See `.erk/reviews/dignified-python.md` and `.claude/skills/dignified-python/references/api-design.md` for the formal exception rules.

## Detection Strategy: Declarative Constraints

<!-- Source: .erk/reviews/dignified-python.md -->

The review system checks exceptions **before flagging**, not after. This prevents false positive noise in PR reviews.

**The decision tree**:

1. Count non-self/cls parameters
2. If ≥5, check for `*` or `*,` on its own line in signature
3. If missing, check decorator stack for `@abstractmethod`, `@click.command()`, `@click.group()`
4. Check class inheritance for `Protocol` base
5. Only flag if none of the above apply

**Why this order matters**: Decorators and inheritance are declarative — the programmer has already signaled "this is special" by using the ABC/Protocol/Click mechanism. The review respects those signals.

## Documenting Exceptions in Code

When a method signature qualifies for an exception, document it in the docstring:

```python
def some_method(
    self,
    param1: str,
    param2: int,
    param3: bool,
    param4: Path,
    param5: list[str],
) -> Result:
    """Do something important.

    Note: Exempt from keyword-only rule (ABC method signature).
    """
    ...
```

**Why document the exception**: Future agents reviewing this code need to know the exemption was intentional, not an oversight. The docstring note short-circuits the "should this have `*`?" question.

## Related Documentation

- `.erk/reviews/dignified-python.md` - Review implementation and exception rules
- `.claude/skills/dignified-python/references/api-design.md` - Keyword-only parameter rationale and patterns
