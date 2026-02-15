---
name: Test Coverage Review
paths:
  - "src/**/*.py"
  - "packages/**/*.py"
  - "tests/**/*.py"
marker: "<!-- test-coverage-review -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Categorize PR Files

Run `gh pr diff` and `gh pr view --json files` to get the full file list and diff.

Categorize every Python file into these buckets:

- **source_added**: New files in `src/` or `packages/` (not in `tests/`)
- **source_modified**: Modified files in `src/` or `packages/` (not in `tests/`)
- **source_deleted**: Deleted files in `src/` or `packages/` (not in `tests/`)
- **tests_added**: New files in `tests/`
- **tests_modified**: Modified files in `tests/`
- **tests_deleted**: Deleted files in `tests/`

**Exclude from analysis** (do not count or flag these):

- `__init__.py` files
- `conftest.py` files
- `__main__.py` files
- Documentation files (`.md`, `.rst`, `.txt`)
- Configuration files (`.toml`, `.cfg`, `.ini`, `.yaml`, `.yml`, `.json`)
- Type stub files (`.pyi`)
- Data files, fixtures, and non-logic files

**Distinguishing significant modifications**: For `source_modified` files, read the diff to determine if changes are significant. Skip files where modifications are only:

- Import reordering or additions
- Type annotation changes
- Whitespace or formatting
- Comment changes

Only count files with new functions, classes, methods, or meaningful logic changes as significant modifications.

## Step 2: Early Exit

Skip the review with a brief summary comment if ANY of these conditions are true:

- PR only touches test files (test-only PR)
- PR only touches docs/config files (no source or test changes)
- No source additions and no significant source modifications

Summary for early exit:

```
### Test Coverage Review
No source additions or significant modifications detected. Skipping coverage analysis.
```

## Step 3: Check Test Coverage for Each Source File

For each file in `source_added` and significantly `source_modified`:

### 3a. Search for corresponding tests

Look for test files matching these patterns:

- `tests/**/test_<filename>.py` (exact match)
- `tests/**/test_<parent>_<filename>.py` (parent directory prefix)
- New test files in `tests_added` that import from the source module

### 3b. Detect legitimately untestable files

Read the source file to check if it is:

- A thin CLI wrapper (only Click decorators and delegation to other modules)
- A type-only file (only type aliases, TypeVar, Protocol definitions)
- An ABC definition file (only abstract method signatures)
- A re-export or barrel file

If the file is legitimately untestable, mark it as excluded with reason.

### 3c. Detect test renames/moves

If `tests_deleted` and `tests_added` both contain files with similar names or overlapping content, treat as a rename rather than a deletion + gap.

## Step 4: Analyze Test Balance

Calculate:

- **Untested source files**: Count of `source_added` files without corresponding tests (excluding legitimately untestable files)
- **Net test change**: `len(tests_added) - len(tests_deleted)`
- **Source-test ratio**: New source lines vs new test lines

Flag conditions:

- **Untested new source files > 0**: New feature code without tests
- **Net test reduction with source additions**: Tests deleted while adding source
- **Non-trivial source added with zero test files added**: Significant code with no testing effort

## Step 5: Post Inline Comments

On each untested source file (first line of file):

```
**Test Coverage**: New source file without corresponding tests. Erk requires Layer 4 business logic tests for all feature code.
```

On each deleted test file where the corresponding source still exists:

```
**Test Coverage**: Test file deleted but corresponding source code still exists. This reduces test coverage.
```

## Step 6: Summary Comment

Post a summary comment with this format (preserve existing Activity Log entries and prepend new entry):

```
### Source Files

| File | Status | Tests |
|------|--------|-------|
| `src/path/file.py` | Added | ❌ No tests |
| `src/path/other.py` | Modified | ✅ `tests/test_other.py` |
| `src/path/types.py` | Added | ➖ Excluded (type-only) |

### Flags

- ❌ **N new source file(s) without tests**
- ❌ **Net test reduction: N deleted, M added**

(Only show flags that apply. Omit section if no flags.)

### Excluded Files

- `src/path/__init__.py` — init file
- `src/path/types.py` — type-only file

(Only show if files were excluded.)
```

Activity log entry examples:

- "Found 2 untested source files (submit_pipeline.py, config_loader.py)"
- "All source files have test coverage"
- "1 untested file, net test reduction of 3"
- "No source additions or significant modifications"

Keep the last 10 log entries maximum.
