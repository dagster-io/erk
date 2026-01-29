---
title: Naming Utilities Pattern
read_when:
  - "adding new branch name extraction functions"
  - "working with branch naming conventions"
  - "implementing pattern-based identification"
  - "sanitizing names for filesystem or git use"
tripwires:
  - action: "parsing branch names with regex"
    warning: "Use functions from erk_shared.naming for standard patterns. Don't reinvent extraction logic."
  - action: "sanitizing strings for filesystem use"
    warning: "Use sanitize_worktree_name() or sanitize_branch_component(). Don't write custom sanitization."
---

# Naming Utilities Pattern

`erk_shared.naming` provides a central registry of pure utility functions for branch naming, worktree naming, and pattern extraction. All functions are stateless, testable, and follow LBYL patterns.

## Module Design

**Location**: `packages/erk-shared/src/erk_shared/naming.py` (573 lines, 15 functions)

**Characteristics**:

- **Pure functions**: No I/O, deterministic outputs
- **LBYL patterns**: Check conditions explicitly, no exceptions for control flow
- **Stdlib only**: Uses `re`, `unicodedata`, `datetime`, `pathlib`
- **Type-safe returns**: `int | None` for nullable values, explicit tuples
- **Dependency injection**: Git operations passed as parameters, not globals

## Function Inventory

### Name Sanitization

| Function                         | Purpose                                             | Returns              |
| -------------------------------- | --------------------------------------------------- | -------------------- |
| `sanitize_worktree_name()`       | Convert arbitrary string to worktree directory name | `str` (max 31 chars) |
| `sanitize_branch_component()`    | Convert string to git-safe branch component         | `str` (max 31 chars) |
| `generate_filename_from_title()` | Convert plan title to markdown filename             | `str`                |
| `strip_plan_from_filename()`     | Remove "plan-" prefix from filename                 | `str`                |

### Timestamp Management

| Function                           | Purpose                               | Returns                     |
| ---------------------------------- | ------------------------------------- | --------------------------- |
| `has_timestamp_suffix()`           | Check if name ends with `-MM-DD-HHMM` | `bool`                      |
| `format_branch_timestamp_suffix()` | Format datetime as branch suffix      | `str` (e.g., `-01-15-1430`) |

### Pattern Extraction

| Function                             | Purpose                                                  | Returns                   |
| ------------------------------------ | -------------------------------------------------------- | ------------------------- |
| `extract_trailing_number()`          | Extract number from end of name                          | `tuple[str, int \| None]` |
| `extract_leading_issue_number()`     | Extract issue number from `P{issue}-` pattern            | `int \| None`             |
| `extract_plan_review_issue_number()` | Extract issue number from `plan-review-{issue}-` pattern | `int \| None`             |

### Name Generation

| Function                          | Purpose                               | Returns |
| --------------------------------- | ------------------------------------- | ------- |
| `generate_issue_branch_name()`    | Create branch name from issue + title | `str`   |
| `derive_branch_name_from_title()` | Create branch name from title only    | `str`   |
| `default_branch_for_worktree()`   | Infer branch name from worktree name  | `str`   |

### Uniqueness Helpers

| Function                                  | Purpose                             | Returns |
| ----------------------------------------- | ----------------------------------- | ------- |
| `ensure_unique_worktree_name_with_date()` | Add date suffix to avoid collisions | `str`   |
| `ensure_simple_worktree_name()`           | Add numeric suffix for uniqueness   | `str`   |
| `ensure_unique_worktree_name()`           | General uniqueness helper           | `str`   |

## Extraction Functions Comparison

Two key extraction functions handle different branch patterns:

### extract_leading_issue_number()

Extracts issue numbers from **implementation branches**:

**Pattern**: `^P(\d+)-`

**Examples**:

```python
extract_leading_issue_number("P2382-convert-erk-create-raw-ext")
# Returns: 2382

extract_leading_issue_number("P42-feature-01-15-1430")
# Returns: 42

extract_leading_issue_number("feature-branch")
# Returns: None
```

**Use cases**:

- Correlating implementation PRs with plan issues
- Finding plan issue from feature branch
- Filtering branches by issue number

### extract_plan_review_issue_number()

Extracts issue numbers from **plan review branches**:

**Pattern**: `^plan-review-(\d+)-`

**Examples**:

```python
extract_plan_review_issue_number("plan-review-6214-01-15-1430")
# Returns: 6214

extract_plan_review_issue_number("plan-review-42-01-28-0930")
# Returns: 42

extract_plan_review_issue_number("P2382-feature")
# Returns: None
```

**Use cases**:

- Identifying plan review PRs
- Finding which plan a review PR addresses
- Checking for existing review PRs before creating new ones

**When to use which**:

- Have a feature branch? Use `extract_leading_issue_number()`
- Have a review branch? Use `extract_plan_review_issue_number()`
- Unknown branch type? Try both, check which returns non-None

## Return Type Pattern: int | None

Extraction functions return `int | None` instead of raising exceptions or returning sentinel values:

```python
# Good: Explicit None handling via LBYL
issue_number = extract_leading_issue_number(branch_name)
if issue_number is None:
    # No issue number in branch, handle gracefully
    return handle_no_issue_case()

# Use the issue number (type narrowed to int)
pr = find_pr_for_issue(issue_number)
```

**Why this pattern**:

- **LBYL-friendly**: Check for None before using
- **Type-safe**: Type checkers understand `int | None`
- **No exceptions**: Missing patterns are expected, not exceptional
- **Explicit**: Caller must handle None case

## Testing Pattern

Functions use parametrized tests covering valid, invalid, and edge cases:

```python
@pytest.mark.parametrize(
    "branch_name,expected",
    [
        # Valid cases
        ("plan-review-6214-01-15-1430", 6214),
        ("plan-review-42-01-28-0930", 42),
        # Invalid cases
        ("P2382-feature", None),
        ("feature-branch", None),
        ("plan-review-", None),
        # Edge cases
        ("plan-review-0-01-15-1430", 0),
    ],
)
def test_extract_plan_review_issue_number(branch_name: str, expected: int | None):
    assert extract_plan_review_issue_number(branch_name) == expected
```

**Test source**: `tests/unit/test_naming.py`

## Adding New Patterns

When adding a new branch naming pattern extraction:

### 1. Define the Pattern

Document the regex and provide examples in docstring:

```python
def extract_my_pattern(branch_name: str) -> int | None:
    """Extract number from my-pattern-{number}- branch naming convention.

    Pattern: my-pattern-{number}-{anything}
    Examples: "my-pattern-123-feature", "my-pattern-42-01-15-1430"

    Args:
        branch_name: Branch name to parse

    Returns:
        Number if branch matches pattern, else None

    Examples:
        >>> extract_my_pattern("my-pattern-123-feature")
        123
        >>> extract_my_pattern("other-branch")
        None
    """
    match = re.match(r"^my-pattern-(\d+)-", branch_name)
    if match:
        return int(match.group(1))
    return None
```

### 2. Write Parametrized Tests

Cover valid, invalid, and edge cases:

```python
@pytest.mark.parametrize(
    "branch_name,expected",
    [
        ("my-pattern-123-feature", 123),
        ("my-pattern-0-feature", 0),
        ("other-pattern-123", None),
        ("my-pattern-", None),
        ("", None),
    ],
)
def test_extract_my_pattern(branch_name: str, expected: int | None):
    assert extract_my_pattern(branch_name) == expected
```

### 3. Add to Function Inventory

Update this document's function inventory table with the new function.

### 4. Document Use Cases

Explain when to use the new extraction function vs. existing ones.

## Anti-Patterns

### ❌ Reinventing Sanitization

```python
# WRONG: Custom sanitization logic
def clean_name(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")
```

**Problem**: Doesn't handle unicode, special chars, length limits.

**Fix**: Use `sanitize_worktree_name()` or `sanitize_branch_component()`.

### ❌ Hardcoding Regex in Call Sites

```python
# WRONG: Inline pattern matching
match = re.match(r"^P(\d+)-", branch_name)
if match:
    issue_number = int(match.group(1))
```

**Problem**: Duplicates logic, breaks when pattern changes.

**Fix**: Use `extract_leading_issue_number()`.

### ❌ Raising Exceptions for Missing Patterns

```python
# WRONG: Exception for expected case
def extract_number(name: str) -> int:
    match = re.match(r"^P(\d+)-", name)
    if not match:
        raise ValueError("No issue number found")
    return int(match.group(1))
```

**Problem**: Missing patterns are not exceptional, they're expected.

**Fix**: Return `int | None`, let caller handle None via LBYL.

### ❌ Using Sentinel Values

```python
# WRONG: Magic number sentinel
def extract_number(name: str) -> int:
    match = re.match(r"^P(\d+)-", name)
    if not match:
        return -1  # Sentinel
    return int(match.group(1))
```

**Problem**: Caller must remember -1 means "not found", type system doesn't help.

**Fix**: Return `int | None`, type system enforces None checks.

## Related Topics

- [Conventions](../conventions.md) - Erk naming conventions (branch, worktree, CLI commands)
- [PR Discovery](../planning/pr-discovery.md) - Using extraction functions to find PRs
- [Dignified Python](../../.claude/skills/dignified-python/) - LBYL patterns, stdlib-only design
