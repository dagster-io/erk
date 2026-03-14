---
title: Test Fakes Directory Structure
read_when:
  - "creating test fakes"
  - "moving fakes from production to test packages"
  - "organizing test doubles"
tripwires:
  - action: "creating a fake in src/"
    warning: "Fakes live in tests/fakes/, not production code"
    doc: "testing/fakes-directory-structure.md"
---

# Test Fakes Directory Structure

## Rule

Test fakes MUST live in `tests/fakes/`, NOT in production packages under `src/`.

## Directory Structure

```
tests/fakes/
├── __init__.py
├── gateway/
│   ├── __init__.py
│   ├── pr_service.py
│   ├── github_issues.py
│   ├── git_worktree.py
│   ├── graphite_branch_ops.py
│   └── ...
└── tests/
    ├── __init__.py
    ├── context.py
    ├── prompt_executor.py
    └── ...
```

## Rationale

- Production packages should not contain test infrastructure
- Fakes are test doubles, not production code
- Keeps import boundaries clean
- Prevents accidental production use of fakes

## Migration Pattern

When moving fakes from `src/` to `tests/fakes/`:

1. Create matching directory structure under `tests/fakes/`
2. Move fake implementation files
3. Update all test imports to reference new locations
4. Remove old fake files from production packages
5. Verify no production code imports fakes
