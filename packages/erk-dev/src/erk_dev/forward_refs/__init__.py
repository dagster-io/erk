"""Forward reference detection utilities.

This module provides utilities to detect Python files that are at risk of
forward reference errors due to TYPE_CHECKING imports without the required
`from __future__ import annotations` import.

## Why This Exists (Due Diligence)

We investigated whether existing tools (ruff, ty, pyright) could detect this
pattern before building our own solution. They cannot:

### ruff

- **FA102 (future-required-type-annotation)**: Only checks for PEP 585/604
  syntax (`list[int]`, `int | str`) without future annotations. Does NOT
  detect TYPE_CHECKING imports used in annotations.
  https://docs.astral.sh/ruff/rules/future-required-type-annotation/

- **TCH rules (flake8-type-checking)**: Help move imports INTO TYPE_CHECKING
  blocks, but assume you already have future annotations. No rule enforces
  that future annotations are present when TYPE_CHECKING imports exist.
  https://github.com/charliermarsh/ruff/issues/2214

### ty / pyright

Type checkers treat `TYPE_CHECKING` as `True` during static analysis, so
they "see" all the conditional imports. The error only manifests at runtime
when `TYPE_CHECKING` is `False` and Python tries to evaluate the annotation.
This is why type checkers cannot catch this class of bug.

### The Gap

There is no existing linter rule that enforces:
"If you have TYPE_CHECKING imports, you must have future annotations."

This module fills that gap with static AST analysis.

## The Pattern We Detect

This pattern causes NameError at runtime:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType  # Only imported at type-check time

def process(x: MyType) -> MyType:  # NameError: 'MyType' not defined
    return x
```

The fix is simple - add future annotations:

```python
from __future__ import annotations  # Makes annotations strings, not evaluated
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType

def process(x: MyType) -> MyType:  # Works! Annotation is now a string
    return x
```
"""

# Import from erk_dev.forward_refs.detection directly
