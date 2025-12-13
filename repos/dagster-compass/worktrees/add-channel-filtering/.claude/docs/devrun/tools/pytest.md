# pytest Execution and Parsing Guide

Comprehensive guide for executing pytest commands and parsing test results.

## Command Detection

Detect pytest in these command patterns:

```bash
pytest
uv run pytest
python -m pytest
```

## Command Patterns

### Basic Invocations

```bash
# Run all tests
pytest

# Run tests in directory
pytest tests/

# Run specific file
pytest tests/test_file.py

# Run specific test function
pytest tests/test_file.py::test_function

# Run tests matching pattern
pytest -k "test_auth"
```

### Common Flags

**Verbosity and Output:**

- `-v, --verbose` - Verbose output with test names
- `-vv` - Extra verbose with full diff output
- `-s, --capture=no` - Don't capture stdout (show print statements)
- `-q, --quiet` - Quiet output
- `--tb=short` - Short traceback format
- `--tb=line` - One line per failure

**Test Selection:**

- `-k EXPRESSION` - Run tests matching name expression
- `-m MARKER` - Run tests with specific marker
- `-x, --exitfirst` - Stop on first failure
- `--lf, --last-failed` - Run only tests that failed last time
- `--ff, --failed-first` - Run failed tests first, then others

**Debugging:**

- `--pdb` - Drop into debugger on failures
- `--pdbcls` - Use custom debugger
- `--trace` - Drop into debugger at start of each test

**Coverage:**

- `--cov=PACKAGE` - Measure code coverage for package
- `--cov-report=term` - Terminal coverage report
- `--cov-report=html` - HTML coverage report
- `--cov-report=xml` - XML coverage report

**Other Useful Flags:**

- `--durations=N` - Show N slowest tests
- `--maxfail=N` - Stop after N failures
- `-n NUM` - Run tests in parallel (requires pytest-xdist)
- `--collect-only` - Show what tests would run without executing

## Output Parsing Patterns

### Success Output

```
============================= test session starts ==============================
collected 47 items

tests/test_config.py ....                                                [ 8%]
tests/test_paths.py ............                                        [ 34%]
tests/test_validation.py .............................                  [100%]

============================== 47 passed in 3.21s ==============================
```

**Extract:**

- Total tests collected: `47 items`
- Tests passed: `47 passed`
- Execution time: `3.21s`
- Success indicator: All dots, no F or E

### Failure Output

```
============================= test session starts ==============================
collected 10 items

tests/test_auth.py .F..                                                  [ 40%]
tests/test_user.py ....F.                                                [100%]

=================================== FAILURES ===================================
_______________________________ test_login_valid _______________________________

    def test_login_valid():
>       assert authenticate("user", "pass") == True
E       AssertionError: assert False == True
E        +  where False = authenticate('user', 'pass')

tests/test_auth.py:15: AssertionError
________________________________ test_user_create ______________________________

    def test_user_create():
>       user = create_user("test")
E       TypeError: create_user() missing 1 required positional argument: 'email'

tests/test_user.py:23: TypeError
=========================== short test summary info ============================
FAILED tests/test_auth.py::test_login_valid - AssertionError: assert False == True
FAILED tests/test_user.py::test_user_create - TypeError: create_user() missing 1 required positional argument: 'email'
========================= 8 passed, 2 failed in 2.15s ==========================
```

**Extract:**

- Failed test names: `test_login_valid`, `test_user_create`
- File locations: `tests/test_auth.py:15`, `tests/test_user.py:23`
- Error types: `AssertionError`, `TypeError`
- Error messages: Full assertion context
- Summary: `8 passed, 2 failed in 2.15s`

### Skipped Tests

```
========================= 5 passed, 2 skipped in 1.23s =========================
```

**Extract:**

- Passed count: `5`
- Skipped count: `2`
- Reasons for skipping (if `-v` used)

### Coverage Output

```
---------- coverage: platform darwin, python 3.13.0-final-0 ----------
Name                     Stmts   Miss  Cover
--------------------------------------------
src/erk/config.py     45      3    93%
src/erk/paths.py      32      0   100%
--------------------------------------------
TOTAL                       77      3    96%
```

**Extract:**

- Coverage percentage per file
- Total coverage: `96%`
- Statements covered vs missed

### Error Output (Collection Failures)

```
============================= test session starts ==============================
ERROR tests/test_broken.py - ImportError: cannot import name 'foo' from 'erk'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.12s ===============================
```

**Extract:**

- Collection errors (import failures, syntax errors)
- Distinguish from test failures
- File with error: `tests/test_broken.py`

## Parsing Strategy

### 1. Check Exit Code

- `0` = All tests passed
- `1` = Tests ran but some failed
- `2` = Test execution interrupted by user
- `3` = Internal error
- `4` = pytest usage error
- `5` = No tests collected

### 2. Extract Summary Line

Look for pattern: `X passed, Y failed, Z skipped in N.NNs`

### 3. Parse Failures

For each `FAILED` line in "short test summary info":

- Extract: `FAILED file::test_name - ErrorType: message`
- Get file location from traceback section
- Capture relevant assertion context

### 4. Extract Counts

- Tests collected: Line with `collected X items`
- Tests passed: Number before `passed` in summary
- Tests failed: Number before `failed` in summary
- Tests skipped: Number before `skipped` in summary
- Tests with errors: Number before `error` in summary

### 5. Coverage Data (if --cov used)

- Look for "coverage:" section
- Extract percentage per file
- Get TOTAL coverage percentage

## Reporting Guidance

### All Tests Pass

**Summary**: "All tests passed (X passed in Y.Ys)"
**Include**: Test count, execution time
**Omit**: Individual test names (unless verbose requested)

### Some Tests Fail

**Summary**: "Test run failed: X passed, Y failed"
**Include**:

- List of failed test names
- File locations and line numbers
- Error types and key messages
- Relevant assertion context

**Omit**: Full traceback unless complex failure

### Collection Error

**Summary**: "Failed to collect tests: [error]"
**Include**:

- Import error details
- File with syntax/import error
- Module/name that couldn't be imported

### No Tests Collected

**Summary**: "No tests collected"
**Include**: Possible reasons (empty test files, wrong directory, -k filter matched nothing)

## Best Practices

1. **Always check exit code first** - it's the most reliable indicator
2. **Parse summary line** - contains all key metrics
3. **Extract failed test details** from "short test summary info" section
4. **Keep successful runs brief** - just counts and time
5. **Provide full context for failures** - test name, location, error type, message
6. **Distinguish test failures from collection errors** - different remediation
7. **Report coverage when available** - but don't make it the focus unless requested
