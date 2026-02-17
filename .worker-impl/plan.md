# Remove @pytest.mark.integration markers to fix PytestUnknownMarkWarning

## Context

The files `tests/integration/test_docs_check.py` and `tests/integration/test_real_agent_docs.py` use `@pytest.mark.integration` decorators on their test functions. However, the `integration` marker is not registered in `pyproject.toml` under `[tool.pytest.ini_options]` (there is no `markers` key at all). This causes `PytestUnknownMarkWarning` warnings when running tests.

Since these tests already live in the `tests/integration/` directory (which is the organizational convention for integration tests), the `@pytest.mark.integration` markers are redundant. The correct fix is to remove the markers rather than register them.

## Changes

### File 1: `tests/integration/test_docs_check.py`

Remove the `@pytest.mark.integration` decorator from all three test functions:

- Line 45: Remove `@pytest.mark.integration` above `test_check_passes_with_valid_docs_in_sync`
- Line 66: Remove `@pytest.mark.integration` above `test_check_fails_with_invalid_frontmatter`
- Line 84: Remove `@pytest.mark.integration` above `test_check_fails_when_sync_out_of_date`

Also remove the `import pytest` statement on line 9 if it becomes unused after removing the markers. Check whether `pytest` is used elsewhere in the file (e.g., `pytest.fixture`, `pytest.raises`, `pytest.param`, `tmp_path` fixture type hints). In this file, `pytest` is NOT used for anything other than the markers, so the import should be removed.

### File 2: `tests/integration/test_real_agent_docs.py`

Remove the `@pytest.mark.integration` decorator from both test functions:

- Line 11: Remove `@pytest.mark.integration` above `test_format_markdown_normalizes_content`
- Line 25: Remove `@pytest.mark.integration` above `test_format_markdown_is_idempotent`

Also remove the `import pytest` statement on line 7 since `pytest` is not used for anything else in this file.

## Files NOT Changing

- `pyproject.toml` — We are NOT adding a `markers` registration. The markers are simply unnecessary.
- No other test files — These are the only two files using `@pytest.mark.integration`.

## Verification

1. Run `ruff check tests/integration/test_docs_check.py tests/integration/test_real_agent_docs.py` to confirm no lint errors (unused imports, etc.)
2. Run `pytest tests/integration/test_docs_check.py tests/integration/test_real_agent_docs.py -W error::pytest.PytestUnknownMarkWarning` to confirm the warnings are gone
3. Run `pytest tests/integration/test_docs_check.py tests/integration/test_real_agent_docs.py` to confirm tests still pass