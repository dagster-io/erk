---
title: Import Alias vs Re-Export Detection
read_when:
  - enforcing the no-import-aliases rule, building automated alias detection, distinguishing re-exports from alias violations
tripwires:
  - action: "flagging `import X as X` or `from .mod import Y as Y` as a violation"
    warning: "The `X as X` form is an explicit re-export marker, not an alias. Only flag when the alias differs from the original name."
  - action: "allowing `import X as Y` because it's a common convention (e.g., `import pandas as pd`)"
    warning: "Erk prohibits ALL gratuitous import aliases. The only exception is resolving genuine name collisions between two modules."
---

# Import Alias vs Re-Export Detection

## Why This Matters

Erk prohibits import aliases (`import X as Y` where X != Y) because they fragment grep-based symbol discovery — searching for a module name misses files that aliased it. But Python's `import X as X` syntax is a legitimate re-export marker used at package boundaries. Any automated enforcement must distinguish these two syntactically similar but semantically opposite patterns.

This is cross-cutting because the rule affects all Python files, the re-export exception affects `__init__.py` files specifically, and enforcement touches linting, agent review, and the dignified-python skill.

## The Distinction

| Pattern              | Example                                        | Meaning                       | Allowed?   |
| -------------------- | ---------------------------------------------- | ----------------------------- | ---------- |
| Standard import      | `import foo`                                   | Normal usage                  | Yes        |
| Named import         | `from foo import Bar`                          | Normal usage                  | Yes        |
| Re-export marker     | `from .internal import Widget as Widget`       | Explicit public API re-export | Yes        |
| Collision resolution | `from datetime import datetime as dt_datetime` | Two modules export same name  | Yes (rare) |
| Gratuitous alias     | `import foo as f`                              | Shorthand for convenience     | **No**     |
| Convention alias     | `import pandas as pd`                          | Common but forbidden in erk   | **No**     |

The critical detection challenge: `import X as X` and `import X as Y` differ only in whether the alias matches the original name. A naive "flag everything with `as`" approach produces false positives on re-exports. A regex negative lookahead (`(?!\1\b)`) or AST-based comparison handles this correctly.

## Why Not Use Ruff/Flake8?

Ruff's `ICN` (import conventions) rules enforce _specific_ alias conventions (e.g., requiring `import pandas as pd`), which is the opposite of erk's goal. No standard linter rule maps to "reject all aliases except identity re-exports." Enforcement currently relies on agent awareness via the dignified-python skill and code review rather than automated tooling.

## The One Exception

Genuine name collisions — where two different modules export identically-named symbols needed in the same file — are the only case where aliasing is acceptable. This is rare enough that it should be commented when it occurs, explaining which collision is being resolved.

## Related Documentation

- The canonical rule definition and rationale live in the dignified-python skill (No Import Aliases section)
- [Heredoc Quoting](../architecture/bash-python-integration.md) — relevant if building bash-based detection scripts, since regex patterns containing `\s` and `\w` require quoted heredocs
