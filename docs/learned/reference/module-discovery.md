---
title: Module Location Discovery
read_when:
  - "searching for Python modules in monorepo"
  - "when Glob fails to find expected modules"
---

# Module Location Discovery in Monorepo

When Glob patterns fail to locate a Python module, use the import trick:

```bash
python3 -c "import erk_shared.gateway.github.metadata.roadmap; print(erk_shared.gateway.github.metadata.roadmap.__file__)"
```

## When to Use

- Glob pattern `**/modulename.py` returns no results
- Module might be in an unexpected package location
- Monorepo has multiple packages with similar structures

## Why This Works

Python's import system resolves the actual file path regardless of where it lives in the directory structure. This bypasses the need to know which package directory a module lives in.
