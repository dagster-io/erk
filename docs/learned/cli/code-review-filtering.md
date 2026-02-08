---
title: Code Review Filtering
read_when:
  - "debugging false positives in code review"
  - "understanding keyword-only parameter exceptions"
  - "working with ABC/Protocol method validation"
tripwires:
  - action: "flagging 5+ parameter violations"
    warning: "Before flagging 5+ parameter violations, verify NO exception applies (ABC/Protocol/Click)"
---

# Code Review Filtering

## Why Exception Filtering Matters

Code reviews enforce dignified-python patterns, but certain structural constraints make some rules impossible to follow. The keyword-only parameter rule (5+ parameters must use `*` separator) exists to improve call-site readability, but breaks down when signatures are constrained by external contracts.

**The core tension**: We want readable call sites in application code, but interface definitions (ABC/Protocol) and framework callbacks (Click) have different priorities. Interface definitions optimize for contract clarity, not call-site readability. Framework callbacks follow the framework's injection rules, not our preferences.

Exception filtering lets the review system distinguish "can't follow the rule due to constraints" from "chose not to follow the rule."

## Exception Categories and Rationale

<!-- Source: .github/reviews/dignified-python.md, lines 80-88 -->
<!-- Source: .claude/skills/dignified-python/references/api-design.md, lines 112-141 -->

### ABC and Protocol Methods: Exempt

**Why interfaces are different**: ABC and Protocol methods define contracts that implementations must honor. The signature is the contract. Adding `*` to an interface method forces ALL implementations to match, even when some implementations only have 2-3 parameters (common after implementing the interface with delegation or simpler logic).

**The trap**: If we enforce keyword-only on interfaces, refactoring an implementation to simplify its parameters creates a signature mismatch. The implementation is less complex than the interface, but can't drop the `*` separator without violating the contract.

See the exception documentation in `.github/reviews/dignified-python.md` (lines 80-88) and `.claude/skills/dignified-python/references/api-design.md` for the formal exception rules.

### Click Command Callbacks: Exempt

**Why framework injection wins**: Click injects parameters positionally based on decorator order. The decorators define the signature, not the function parameter list. Adding `*` to a Click callback breaks the framework's injection mechanism.

**The constraint**: Click's `@click.option()` decorators process arguments in order and pass them positionally to the callback. Keyword-only parameters after `*` don't receive injected values correctly because Click doesn't know about the separator.

### Context Objects: Allowed as First Positional

**Why `ctx` stays positional**: Context objects (`ctx`, `self`, `cls`) carry ambient state and infrastructure. They're not data parameters — they're plumbing. Requiring `ctx` to be keyword-only (`func(*, ctx=ctx, ...)`) is verbose ceremony that adds no clarity.

**The pattern**: Context objects can remain positional as the first parameter, followed by `*` for remaining parameters. This balances readability (short, conventional context passing) with explicitness (data parameters are keyword-only).

## Detection Strategy: Declarative Constraints

<!-- Source: .github/reviews/dignified-python.md, lines 80-88 -->

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

- `.github/reviews/dignified-python.md` - Review implementation and exception rules
- `.claude/skills/dignified-python/references/api-design.md` - Keyword-only parameter rationale and patterns
