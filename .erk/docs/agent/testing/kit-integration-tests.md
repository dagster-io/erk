---
title: Kit Integration Test Patterns
read_when:
  - "writing tests for kit structure validation"
  - "updating tests after kit structure changes"
  - "test failures in test_dignified_python_sync"
  - "verifying installed kit artifacts match expectations"
---

# Kit Integration Test Patterns

Integration tests in `tests/integration/kits/kits/` validate installed kit structure and consistency.

## Purpose

These tests verify:

1. Kit artifacts are installed to correct locations
2. Kit documentation structure matches expectations
3. Skills reference correct documentation paths
4. No version-specific language in universal files

## Key Characteristics

- **Tests check INSTALLED artifacts** - Not kit source files
- **Path resolution uses relative traversal** - `Path(__file__).parent.parent...` to find project root
- **Tests may become stale** - When kit structure changes, tests need updating

## Example: dignified-python Sync Tests

`test_dignified_python_sync.py` validates:

1. **Universal docs exist** at `.erk/docs/kits/dignified-python/`
2. **Version-specific dirs exist** for each Python version (310, 311, 312, 313)
3. **SKILL.md files reference correct doc paths** using `@.erk/docs/kits/` syntax
4. **No version-specific language** in universal files

## Path Resolution Pattern

Tests use relative path traversal to find the project root:

```python
# From tests/integration/kits/kits/ -> go up 5 levels to project root
repo_root = Path(__file__).parent.parent.parent.parent.parent
docs_dir = repo_root / ".erk" / "docs" / "kits" / "dignified-python"
```

## When Kit Structure Changes

After modifying kit artifacts or documentation locations:

1. **Update test path references** - e.g., `.claude/docs/` → `.erk/docs/kits/`
2. **Update expected file lists** - Match actual kit contents
3. **Run tests to verify**:
   ```bash
   uv run pytest tests/integration/kits/kits/test_dignified_python_sync.py -v
   ```

## Common Test Patterns

### Verifying File Existence

```python
def test_required_files_exist():
    """Verify required documentation files exist."""
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    docs_dir = repo_root / ".erk" / "docs" / "kits" / "my-kit"

    required_files = ["core.md", "guide.md"]

    for filename in required_files:
        file_path = docs_dir / filename
        if not file_path.exists():
            pytest.fail(f"Required file missing: {file_path}")
```

### Verifying @ Reference Paths

```python
def test_skill_references_correct_paths():
    """Verify SKILL.md references correct documentation paths."""
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    skill_md = repo_root / "packages" / "erk-kits" / ... / "SKILL.md"

    content = skill_md.read_text(encoding="utf-8")

    expected_path = "@.erk/docs/kits/my-kit/"
    if expected_path not in content:
        pytest.fail(f"SKILL.md does not reference {expected_path}")
```

### Validating Content Patterns

```python
def test_no_prohibited_content():
    """Verify universal files don't contain prohibited patterns."""
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    docs_dir = repo_root / ".erk" / "docs" / "kits" / "my-kit"

    prohibited_patterns = ["Python 3.13+", "3.13 and above"]

    for file_path in docs_dir.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")

        for pattern in prohibited_patterns:
            if pattern in content:
                pytest.fail(f"{file_path.name} contains prohibited: '{pattern}'")
```

## Directory Structure

```
tests/integration/kits/
├── kits/
│   ├── test_dignified_python_sync.py  # Structure validation
│   ├── erk/
│   │   ├── test_check_impl_integration.py
│   │   └── ...
│   └── gt/
│       └── ...
└── packaging/
    └── test_wheel_contents.py          # Package validation
```

## Related Documentation

- [Kit Documentation Installation](../kits/doc-installation.md) - Where docs get installed
- [Artifact Path Transformation](../kits/artifact-path-transformation.md) - Path mapping details
- [@ Reference Resolution](../kits/at-reference-resolution.md) - How @ references work in kits
