---
title: Source Pointer Best Practices
read_when:
  - "choosing between function-name and line-number source pointers"
  - "writing documentation references that resist staleness"
  - "deciding what to point to in a source pointer"
tripwires:
  - action: "using line numbers in source pointers for Python code with named symbols"
    warning: "Prefer function/class name anchors over line numbers. Names survive refactoring; line numbers go stale silently. See source-pointer-best-practices.md."
    score: 5
---

# Source Pointer Best Practices

This document covers best practices for writing source pointers that resist staleness. For the canonical format and enforcement rules, see [source-pointers.md](source-pointers.md).

## Function-Name Anchors vs Line-Number Pointers

| Approach                 | Example                           | Staleness Risk                  | Use When                               |
| ------------------------ | --------------------------------- | ------------------------------- | -------------------------------------- |
| **Function-name anchor** | `lifecycle.py, _build_indicators` | Low — names survive refactoring | Python/TypeScript with named symbols   |
| **Line-number pointer**  | `lifecycle.py:225-234`            | High — any edit shifts numbers  | Markdown, YAML, config without symbols |

**Default to function-name anchors.** They are greppable, survive refactoring, and immediately tell the reader what to look for.

## Stability Hierarchy

When choosing what to point to, prefer more stable targets:

1. **ABC method definitions** — abstract interfaces change rarely
2. **Frozen dataclass/schema fields** — data shapes are stable
3. **Public method names** — preserved during refactoring
4. **Private method names** — may be renamed during refactoring
5. **Line numbers** — any edit shifts them (last resort)

## When Line Numbers Are Acceptable

- Files without named symbols (markdown, YAML, config)
- HTML comment blocks within structured formats
- Specific YAML stanzas in CI workflow files

Even with line numbers, include enough context that a reader can find the section if lines shift:

```markdown
<!-- Source: .github/workflows/plan-implement.yml:42-58, concurrency config section -->
```

## Compound Pointers

For references spanning multiple locations, use multiple source comments:

```markdown
<!-- Source: src/erk/core/llm_json.py, extract_json_dict -->
<!-- Source: src/erk/core/plan_duplicate_checker.py, check_duplicate -->

The extraction function in `llm_json.py` is called by `check_duplicate()` in `plan_duplicate_checker.py`.
```

## Related Documentation

- [Source Pointers](source-pointers.md) — Canonical format and enforcement rules
- [Stale Code Blocks](stale-code-blocks-are-silent-bugs.md) — Why pointers beat embedded code
- [Audit Methodology](audit-methodology.md) — How audits classify documentation quality
