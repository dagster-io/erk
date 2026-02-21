---
title: Test Coverage Detection
read_when:
  - "understanding how the test-coverage-review bot maps source to test files"
  - "debugging false positives in test coverage review"
  - "adding test files in the correct location for coverage detection"
tripwires:
  - action: "placing test files outside both tests/ and packages/*/tests/ directories"
    warning: "The test-coverage-review bot only searches tests/**/ and packages/*/tests/**/ for corresponding test files. Tests placed elsewhere will not be detected and will cause false 'no tests' flags."
---

# Test Coverage Detection

The test-coverage-review bot maps source files to test files using path heuristics. Understanding these heuristics prevents false positive "no tests" flags.

## Source File Patterns

The bot monitors these paths for source changes:

- `src/**/*.py` — Core erk source
- `packages/**/*.py` — Shared packages source

Files in `tests/` are categorized separately as test files.

## Single Test Location

All test files must live in `tests/**/`, regardless of source location:

| Source Location               | Test Location |
| ----------------------------- | ------------- |
| `src/erk/...`                 | `tests/**/`   |
| `packages/erk-shared/src/...` | `tests/**/`   |

## Mapping Heuristics

For each source file, the bot searches for test files using three strategies:

### 1. Exact Match

```
src/erk/cli/commands/submit.py → tests/**/test_submit.py
```

The test filename is `test_<source_filename>.py`.

### 2. Parent Directory Prefix

```
src/erk/cli/commands/pr/check_cmd.py → tests/**/test_pr_check_cmd.py
```

When the source file is nested, the parent directory name is prefixed: `test_<parent>_<filename>.py`.

### 3. Import Analysis

New test files in the PR (in `tests_added`) are checked for imports from the source module. This catches test files with non-standard naming.

## Excluded Files

These file types are excluded from coverage analysis entirely:

- `__init__.py` files
- `conftest.py` files
- `__main__.py` files
- Type stub files (`.pyi`)
- Documentation, configuration, and data files

Additionally, files detected as "legitimately untestable" are excluded:

- Thin CLI wrappers (only Click decorators and delegation)
- Type-only files (only type aliases, TypeVar, Protocol definitions)
- ABC definition files (only abstract method signatures)
- Re-export or barrel files

See [Test Coverage Review Agent](../reviews/test-coverage-agent.md) for the full architectural rationale behind these exclusions.

## Related Documentation

- [Test Coverage Review Agent](../reviews/test-coverage-agent.md) - Architecture and design decisions
- [Automated Review System](automated-review-system.md) - Overview of all review bots
- [Convention-Based Code Reviews](convention-based-reviews.md) - How reviews are configured and discovered
