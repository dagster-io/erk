# Register 'integration' pytest mark in pyproject.toml

## Context

Tests in `tests/integration/test_docs_check.py` and `tests/integration/test_real_agent_docs.py` use `@pytest.mark.integration` but this custom mark is not registered in pytest configuration. This causes `PytestUnknownMarkWarning` warnings during test runs. Registering the mark in `[tool.pytest.ini_options]` eliminates the warnings.

## Changes

### File: `pyproject.toml`

Add a `markers` list to the existing `[tool.pytest.ini_options]` section. The section currently ends at line 125 (after `filterwarnings`). Add the `markers` configuration after the `filterwarnings` block.

**Current state** (lines 118-126):
```toml
[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests", "packages/erk-dev/tests", "packages/erk-statusline/tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
filterwarnings = [
    "ignore:codecs.open\\(\\) is deprecated:DeprecationWarning:frontmatter",
]
```

**After change:**
```toml
[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests", "packages/erk-dev/tests", "packages/erk-statusline/tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
filterwarnings = [
    "ignore:codecs.open\\(\\) is deprecated:DeprecationWarning:frontmatter",
]
markers = [
    "integration: marks tests as integration tests (require external tools like prettier, git, gh)",
]
```

The marker description should convey that integration tests depend on external tools/services, which is the convention established by the existing test files (e.g., `test_docs_check.py` uses prettier, `test_real_agent_docs.py` uses prettier).

## Files NOT changing

- `tests/integration/test_docs_check.py` — already uses `@pytest.mark.integration` correctly
- `tests/integration/test_real_agent_docs.py` — already uses `@pytest.mark.integration` correctly
- No other test files need changes since `integration` is the only unregistered custom mark
- `CHANGELOG.md` — never modified directly

## Verification

1. Run `pytest --co -q tests/integration/test_docs_check.py tests/integration/test_real_agent_docs.py 2>&1 | grep -i "PytestUnknownMarkWarning"` — should produce no output (no warnings)
2. Run `pytest --markers | grep integration` — should show the registered marker with its description
3. Run `ruff check pyproject.toml` — should pass (though ruff doesn't lint TOML, this confirms no syntax issues)
4. Run full test suite to confirm no regressions