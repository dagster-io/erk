# pyright Execution and Parsing Guide

Comprehensive guide for executing pyright commands and parsing type checking results.

## Command Detection

Detect pyright in these command patterns:

```bash
pyright
uv run pyright
python -m pyright
```

## Command Patterns

### Basic Invocations

```bash
# Check all files in project
pyright

# Check specific directory
pyright src/

# Check specific file
pyright src/module.py

# Check multiple paths
pyright src/ tests/
```

### Common Flags

**Output Control:**

- `--verbose` - Verbose output with detailed diagnostics
- `--outputjson` - Output results in JSON format
- `--stats` - Display timing and performance statistics

**Watch Mode:**

- `--watch` - Watch mode for continuous checking
- `--watchport PORT` - Specify port for watch mode

**Type Checking:**

- `--level {basic,standard,strict}` - Type checking level
- `--pythonversion VERSION` - Target Python version
- `--pythonplatform PLATFORM` - Target platform

**Stubs and Libraries:**

- `--createstub PACKAGE` - Create type stub for package
- `--verifytypes PACKAGE` - Verify library type completeness
- `--ignoreexternal` - Ignore external imports

**Project:**

- `--project PATH` - Path to pyrightconfig.json
- `--skipunannotated` - Skip analysis of unannotated functions

## Output Parsing Patterns

### Success Output

```
pyright 1.1.339
0 errors, 0 warnings, 0 informations
Completed in 1.234sec
```

**Extract:**

- Error count: `0 errors`
- Warning count: `0 warnings`
- Info count: `0 informations`
- Execution time: `1.234sec`
- Success indicator: All counts are 0

### Type Error Output

```
/path/to/src/module.py
  /path/to/src/module.py:42:15 - error: Type "str" cannot be assigned to declared type "int"
    "str" is incompatible with "int" (reportAssignmentType)
  /path/to/src/module.py:45:20 - error: Cannot access member "foo" for type "None"
    Member "foo" is unknown (reportAttributeAccess)

/path/to/src/other.py
  /path/to/src/other.py:10:5 - error: Argument of type "list[str]" cannot be assigned to parameter "items" of type "list[int]" in function "process"
    "list[str]" is incompatible with "list[int]" (reportArgumentType)

3 errors, 0 warnings, 0 informations
Completed in 0.987sec
```

**Extract:**

- File paths: `/path/to/src/module.py`, `/path/to/src/other.py`
- Error locations: `line:column` format (e.g., `42:15`)
- Error types: `reportAssignmentType`, `reportAttributeAccess`, `reportArgumentType`
- Error messages: Full type incompatibility descriptions
- Summary: `3 errors, 0 warnings, 0 informations`

### Warning Output

```
/path/to/src/utils.py
  /path/to/src/utils.py:15:8 - warning: "datetime" is not accessed (reportUnusedImport)
  /path/to/src/utils.py:28:4 - information: Type of "result" is "str | int"

0 errors, 1 warning, 1 information
Completed in 0.543sec
```

**Extract:**

- Warnings: Unused imports, potential issues
- Informations: Type inference results (when verbose)
- Distinction between severity levels

### Configuration Error

```
pyright 1.1.339
No configuration file found.
No pyproject.toml file found.
Assuming Python version 3.11
Assuming Python platform Linux
0 errors, 0 warnings, 0 informations
Completed in 1.123sec
```

**Extract:**

- Configuration status
- Assumed defaults
- Still completes successfully if no config found

### Import Error

```
/path/to/src/main.py
  /path/to/src/main.py:5:24 - error: Import "erk.missing" could not be resolved (reportMissingImport)

1 error, 0 warnings, 0 informations
Completed in 0.234sec
```

**Extract:**

- Import resolution failures
- Module that couldn't be found
- File attempting the import

## Parsing Strategy

### 1. Check Exit Code

- `0` = No errors (warnings/info may exist)
- `1` = Type errors found
- Non-zero = Execution error or type errors

### 2. Extract Summary Line

Look for pattern: `X errors, Y warnings, Z informations`

### 3. Parse Errors by File

Group errors by file path:

- File header: `/path/to/file.py`
- Error lines: `  /path/to/file.py:line:col - severity: message`
- Additional context lines (indented further)

### 4. Extract Error Details

For each error line:

- **Location**: `line:column`
- **Severity**: `error`, `warning`, or `information`
- **Message**: Description of type issue
- **Rule**: In parentheses (e.g., `(reportAssignmentType)`)

### 5. Handle Multi-line Errors

Some errors span multiple lines:

- First line: Location and main message
- Following indented lines: Additional context

## Error Rule Categories

Common pyright error rules:

- `reportGeneralTypeIssues` - General type mismatches
- `reportAssignmentType` - Type assignment incompatibilities
- `reportArgumentType` - Function argument type issues
- `reportReturnType` - Return type mismatches
- `reportAttributeAccess` - Unknown attribute access
- `reportMissingImport` - Import resolution failures
- `reportUnusedImport` - Unused imports
- `reportUnusedVariable` - Unused variables
- `reportOptionalMemberAccess` - Accessing members on Optional types
- `reportOptionalSubscript` - Subscripting Optional types

## Reporting Guidance

### All Type Checks Pass

**Summary**: "Type checking passed: 0 errors found (analyzed X files in Y.Ys)"
**Include**: File count, execution time
**Omit**: Detailed file list

### Type Errors Found

**Summary**: "Type checking failed: X errors, Y warnings"
**Include**:

- List of errors grouped by file
- Location (line:column) for each error
- Error message and type incompatibility
- Rule code (reportXYZ)

**Omit**: Overly verbose type hierarchy details

### Configuration Issues

**Summary**: "Pyright completed with configuration warnings"
**Include**:

- Missing config file warnings
- Assumed defaults
- Still report success if no actual errors

### Import Resolution Failures

**Summary**: "Type checking found import errors"
**Include**:

- Which imports couldn't be resolved
- Which files attempted the imports
- Suggestion to check dependencies

## Best Practices

1. **Always check exit code** - most reliable success indicator
2. **Parse summary line first** - get error/warning/info counts
3. **Group errors by file** - easier to understand and fix
4. **Include line:column locations** - precise error positioning
5. **Keep successful runs brief** - just file count and time
6. **Provide full error context** - type incompatibility details matter
7. **Distinguish errors from warnings** - different severity
8. **Note configuration issues** - but don't fail on missing config
