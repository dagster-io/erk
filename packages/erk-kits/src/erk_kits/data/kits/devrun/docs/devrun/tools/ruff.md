# ruff Execution and Parsing Guide

Comprehensive guide for executing ruff commands and parsing linting/formatting results.

## Command Detection

Detect ruff in these command patterns:

```bash
ruff check
ruff format
uv run ruff check
uv run ruff format
python -m ruff check
python -m ruff format
```

## Command Patterns

### Linting Commands

```bash
# Check all files
ruff check

# Check specific directory
ruff check src/

# Check specific file
ruff check src/module.py

# Check and auto-fix
ruff check --fix

# Check with unsafe fixes
ruff check --fix --unsafe-fixes

# Show available fixes without applying
ruff check --show-fixes

# Show statistics
ruff check --statistics
```

### Formatting Commands

```bash
# Format all files
ruff format

# Format specific directory
ruff format src/

# Format specific file
ruff format src/module.py

# Check formatting without writing
ruff format --check

# Show what would be formatted
ruff format --diff
```

### Common Flags

**Linting Flags:**

- `--fix` - Auto-fix violations where possible
- `--unsafe-fixes` - Apply unsafe fixes (may change behavior)
- `--show-fixes` - Show available fixes without applying
- `--watch` - Watch mode for continuous checking
- `--statistics` - Show violation counts by rule
- `--output-format {text,json,junit,grouped}` - Output format
- `--select RULES` - Enable specific rules
- `--ignore RULES` - Disable specific rules
- `--extend-select RULES` - Extend enabled rules
- `--preview` - Enable preview rules
- `--no-cache` - Disable caching

**Formatting Flags:**

- `--check` - Check if files would be formatted
- `--diff` - Show diff of formatting changes
- `--config PATH` - Path to ruff.toml or pyproject.toml

## Output Parsing Patterns

### Successful Check (No Violations)

```
All checks passed!
```

**Extract:**

- Success indicator
- No violations found

### Violations Found (Linting)

```
src/module.py:42:15: F841 Local variable `x` is assigned to but never used
src/module.py:45:1: E501 Line too long (112 > 100 characters)
src/other.py:10:8: UP007 Use `X | Y` for union types
src/other.py:15:1: I001 Import block is un-sorted or un-formatted
Found 4 errors.
[*] 3 fixable with the `--fix` option.
```

**Extract:**

- File locations: `src/module.py:42:15`
- Rule codes: `F841`, `E501`, `UP007`, `I001`
- Messages: Full description of each violation
- Total count: `4 errors`
- Fixable count: `3 fixable`

### Auto-Fixed Violations

```
src/other.py:10:8: UP007 [*] Use `X | Y` for union types
src/other.py:15:1: I001 [*] Import block is un-sorted or un-formatted
Found 4 errors (3 fixed, 1 remaining).
```

**Extract:**

- Fixed violations: Marked with `[*]`
- Fixed count: `3 fixed`
- Remaining count: `1 remaining`

### Format Check Output

```
3 files would be reformatted, 12 files already formatted
```

**Extract:**

- Files needing formatting: `3 files`
- Already formatted: `12 files`

### Format Diff Output

```
--- src/module.py
+++ src/module.py
@@ -10,7 +10,7 @@
 def process(items: list[str]):
-    result=[]
+    result = []
     for item in items:
         result.append(item.strip())
     return result

1 file would be reformatted
```

**Extract:**

- Diff showing formatting changes
- File count: `1 file`

### Statistics Output

```
F841    3
E501    5
UP007   2
I001    1
```

**Extract:**

- Violation counts per rule code

## Rule Categories

### Common ruff Rules

**Pyflakes (F):**

- `F401` - Module imported but unused
- `F841` - Local variable assigned but never used
- `F821` - Undefined name

**pycodestyle (E, W):**

- `E501` - Line too long
- `E402` - Module level import not at top of file
- `W291` - Trailing whitespace

**isort (I):**

- `I001` - Import block is un-sorted or un-formatted

**pyupgrade (UP):**

- `UP007` - Use `X | Y` for union types
- `UP006` - Use `list` instead of `List` for type annotations
- `UP035` - Import from `collections.abc` not `collections`

**flake8-bugbear (B):**

- `B006` - Mutable default argument
- `B007` - Unused loop control variable
- `B008` - Function call in default argument

**Ruff-specific (RUF):**

- `RUF001` - Ambiguous unicode character
- `RUF100` - Unused `noqa` directive

## Parsing Strategy

### 1. Check Exit Code

- `0` = No violations (or all fixed with --fix)
- `1` = Violations found
- `2` = Error in ruff itself

### 2. Detect Operation

- **Linting**: `ruff check` in command
- **Formatting**: `ruff format` in command

### 3. Parse Violations (Linting)

For each violation line:

```
file:line:col: RULE_CODE Message
```

Extract:

- **File**: `file`
- **Location**: `line:col`
- **Rule**: `RULE_CODE`
- **Message**: Violation description
- **Fixable**: `[*]` marker if auto-fixable

### 4. Parse Summary

Look for patterns:

- `Found X errors` or `Found X errors (Y fixed, Z remaining)`
- `X fixable with the --fix option`
- `All checks passed!`

### 5. Parse Formatting Results

Look for patterns:

- `X files would be reformatted, Y files already formatted`
- `X file would be reformatted`
- `X files reformatted`

## Violation Severity

While ruff doesn't have explicit severity levels, rules can be categorized:

**High Priority (Fix immediately):**

- F-series (Pyflakes): Logic errors, undefined names
- B-series (bugbear): Likely bugs

**Medium Priority (Fix soon):**

- E-series (pycodestyle errors): Style violations
- UP-series (pyupgrade): Outdated syntax

**Low Priority (Fix when convenient):**

- W-series (pycodestyle warnings): Minor style issues
- I-series (isort): Import organization

## Reporting Guidance

### All Checks Pass

**Summary**: "All lint checks passed (analyzed X files)"
**Include**: File count if available
**Omit**: Detailed file list

### Violations Found (No Auto-Fix)

**Summary**: "Ruff check found X violations (Y fixable)"
**Include**:

- List of violations with locations
- Rule codes and messages
- Fixable count
- Instruction to use --fix if fixable violations exist

### Violations Auto-Fixed

**Summary**: "Ruff check fixed X violations automatically, Y violations remain"
**Include**:

- Count of fixed violations
- List of remaining violations (if any)

### Format Check (Files Need Formatting)

**Summary**: "Formatting check failed: X files need formatting"
**Include**:

- Count of files needing formatting
- List of file paths that need formatting
- Instruction to use `ruff format` to fix

### Formatting Applied

**Summary**: "Formatted X files successfully"
**Include**:

- Count of reformatted files
- Count of unchanged files

## Best Practices

1. **Check exit code** - reliable success indicator
2. **Distinguish linting from formatting** - different operations
3. **Count fixable vs non-fixable** - informs whether --fix helps
4. **Group violations by file** - easier to understand
5. **Keep successful runs brief** - just confirmation
6. **List all violations** when found - with locations and rule codes
7. **Note auto-fixes** - what was fixed vs what remains
8. **Include rule codes** - helps identify patterns
