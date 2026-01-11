# Extraction → Learn Rename Plan

## Summary

Comprehensive rename of "extraction plans" and related "extraction" terminology to "learn" throughout the codebase. This affects directory names, module imports, class names, function names, constants, string literals, and documentation.

## Scope Distinction: What to Rename vs Keep

### RENAME (Learn Plan Workflow)
- Session extraction for documentation learning
- `PENDING_EXTRACTION_MARKER` and related marker logic
- `ERK_SKIP_EXTRACTION_LABEL`
- `create_raw_extraction_plan()` and related functions
- `RawExtractionResult` type
- `extraction/` module (session discovery, selection, preprocessing)

### KEEP AS-IS (Different Extraction Concepts)
- `diff_extraction.py` - PR diff extraction (not learn-related)
- `test_plan_header_extraction.py` - Header parsing from issues
- `test_metadata_extraction.py` - Metadata parsing

### ALSO RENAME
- `extraction_hints` parameter → `learn_hints` (used in learn workflow)

---

## Phase 1: Directory Renames

### 1.1 Source Code Directories

```bash
# Main extraction module → learn module
git mv packages/erk-shared/src/erk_shared/extraction packages/erk-shared/src/erk_shared/learn

# Empty CLI directory (only has __pycache__) - delete
rm -rf src/erk/cli/commands/plan/extraction
```

### 1.2 Test Directories

```bash
# Unit tests
git mv packages/erk-shared/tests/unit/extraction packages/erk-shared/tests/unit/learn

# Empty CLI test directory - delete
rm -rf tests/commands/plan/extraction
```

### 1.3 File Renames

| Current Path | New Path |
|-------------|----------|
| `packages/erk-shared/src/erk_shared/learn/raw_extraction.py` | `packages/erk-shared/src/erk_shared/learn/raw_learn.py` |
| `packages/erk-shared/tests/unit/learn/test_raw_extraction.py` | `packages/erk-shared/tests/unit/learn/test_raw_learn.py` |
| `tests/commands/submit/test_extraction_plans.py` | `tests/commands/submit/test_learn_plans.py` |
| `docs/learned/architecture/extraction-origin-tracking.md` | `docs/learned/architecture/learn-origin-tracking.md` |
| `.claude/skills/session-inspector/references/extraction.md` | `.claude/skills/session-inspector/references/learn.md` |

---

## Phase 2: Import Statement Updates

### 2.1 Module Imports (~60 files)

Update all imports from `erk_shared.extraction` to `erk_shared.learn`:

```python
# Before
from erk_shared.extraction.raw_extraction import create_raw_extraction_plan
from erk_shared.extraction.types import RawExtractionResult
from erk_shared.extraction.claude_installation import ClaudeInstallation
from erk_shared.extraction.session_context import collect_session_context

# After
from erk_shared.learn.raw_learn import create_raw_learn_plan
from erk_shared.learn.types import RawLearnResult
from erk_shared.learn.claude_installation import ClaudeInstallation
from erk_shared.learn.session_context import collect_session_context
```

Key files requiring import updates:
- `src/erk/cli/commands/plan/learn/create_raw_cmd.py`
- `src/erk/cli/commands/pr/submit_cmd.py`
- `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`
- `src/erk/cli/commands/cc/session/*.py`
- `src/erk/core/context.py`
- `packages/erk-shared/src/erk_shared/context/context.py`
- `packages/erk-shared/src/erk_shared/context/factories.py`

---

## Phase 3: Type/Class Renames

### 3.1 Data Types (`packages/erk-shared/src/erk_shared/learn/types.py`)

```python
# Before
@dataclass(frozen=True)
class RawExtractionResult:
    """Result of creating a raw extraction plan."""
    ...

# After
@dataclass(frozen=True)
class RawLearnResult:
    """Result of creating a raw learn plan."""
    ...
```

---

## Phase 4: Function Renames

### 4.1 Core Functions (`packages/erk-shared/src/erk_shared/learn/raw_learn.py`)

| Current Name | New Name |
|-------------|----------|
| `create_raw_extraction_plan()` | `create_raw_learn_plan()` |
| `get_raw_extraction_body()` | `get_raw_learn_body()` |

### 4.2 Marker Functions (`src/erk/cli/commands/navigation_helpers.py`)

| Current Name | New Name |
|-------------|----------|
| `check_pending_extraction_marker()` | `check_pending_learn_marker()` |

---

## Phase 5: Constant Renames

### 5.1 Markers (`packages/erk-shared/src/erk_shared/scratch/markers.py`)

```python
# Before
PENDING_EXTRACTION_MARKER = "pending-extraction"

# After
PENDING_LEARN_MARKER = "pending-learn"
```

### 5.2 Labels (`packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py`)

```python
# Before
ERK_SKIP_EXTRACTION_LABEL = "erk-skip-extraction"

# After
ERK_SKIP_LEARN_LABEL = "erk-skip-learn"
```

### 5.3 Templates (`packages/erk-shared/src/erk_shared/learn/raw_learn.py`)

```python
# Before
RAW_EXTRACTION_BODY_TEMPLATE = """# Extraction Plan: {branch_name}
...

# After
RAW_LEARN_BODY_TEMPLATE = """# Learn Plan: {branch_name}
...
```

---

## Phase 5.5: Parameter Renames

### 5.5.1 `extraction_hints` → `learn_hints`

Files to update:
- `packages/erk-shared/src/erk_shared/github/metadata/session.py` (function signatures)
- `packages/erk-shared/src/erk_shared/learn/raw_learn.py` (call sites)
- `packages/erk-shared/tests/unit/github/test_session_content.py` (test calls)
- `tests/unit/gateways/github/test_session_content.py` (test calls)
- `.claude/skills/session-inspector/references/learn.md` (documentation)

---

## Phase 6: Module Docstrings and Comments

### 6.1 Module Docstrings

Update docstrings in:
- `packages/erk-shared/src/erk_shared/learn/__init__.py`
- `packages/erk-shared/src/erk_shared/learn/raw_learn.py`
- `packages/erk-shared/src/erk_shared/scratch/markers.py`

### 6.2 Function Docstrings

Update docstrings in functions referencing "extraction":
- `create_raw_learn_plan()` docstring
- `check_pending_learn_marker()` docstring
- Various helper functions

---

## Phase 7: User-Facing Strings

### 7.1 CLI Error Messages (`src/erk/cli/commands/navigation_helpers.py`)

```python
# Before
"Run: erk plan extraction raw\n"
"Or use --force to skip extraction."

# After
"Run: erk plan learn raw\n"
"Or use --force to skip learn."
```

### 7.2 Warning Messages

```python
# Before
"Warning: Skipping pending extraction (--force used).\n"
"Worktree has pending extraction.\n"

# After
"Warning: Skipping pending learn (--force used).\n"
"Worktree has pending learn.\n"
```

### 7.3 Template Content

Update `RAW_LEARN_BODY_TEMPLATE` title and references:
- `# Extraction Plan: {branch_name}` → `# Learn Plan: {branch_name}`
- "Session data for future documentation extraction" → "Session data for future documentation learning"

---

## Phase 8: Documentation Updates

### 8.1 Glossary (`docs/learned/glossary.md`)

Update entries:
- `erk-skip-extraction` → `erk-skip-learn`
- `pending-extraction` → `pending-learn`
- Update all related descriptions

### 8.2 Architecture Docs

- Rename `extraction-origin-tracking.md` → `learn-origin-tracking.md`
- Update content to reference "learn" instead of "extraction"
- Update `docs/learned/architecture/markers.md` references

### 8.3 Index Files

Update routing in:
- `docs/learned/architecture/index.md`
- `docs/learned/index.md`

### 8.4 Conventions Doc (`docs/learned/conventions.md`)

Update import examples referencing `PENDING_EXTRACTION_MARKER`

### 8.5 Skills Documentation

Update `.claude/skills/session-inspector/references/learn.md` (after rename)

---

## Phase 9: Test Updates

### 9.1 Test Class Names

```python
# Before
class TestCreateRawExtractionPlan:
    ...

# After
class TestCreateRawLearnPlan:
    ...
```

### 9.2 Test Function Names

Update test functions in:
- `packages/erk-shared/tests/unit/learn/test_raw_learn.py`
- `tests/commands/submit/test_learn_plans.py`
- `tests/core/test_markers.py`
- `tests/commands/workspace/test_delete.py`
- `packages/erk-shared/tests/unit/github/test_plan_issues.py`

### 9.3 Test Assertions and Fixtures

Update string assertions:
- `"erk-skip-extraction"` → `"erk-skip-learn"`
- `"pending-extraction"` → `"pending-learn"`
- `"Extraction Plan:"` → `"Learn Plan:"`

---

## File-by-File Change Summary

### High-Impact Files (significant changes)

| File | Changes |
|------|---------|
| `packages/erk-shared/src/erk_shared/scratch/markers.py` | Rename constant, update docstrings |
| `packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py` | Rename label constant |
| `packages/erk-shared/src/erk_shared/learn/raw_learn.py` | Rename functions, constants, template |
| `packages/erk-shared/src/erk_shared/learn/types.py` | Rename `RawExtractionResult` |
| `src/erk/cli/commands/navigation_helpers.py` | Rename function, update imports, error messages |
| `src/erk/cli/commands/submit.py` | Update import, label reference |
| `docs/learned/glossary.md` | Update multiple entries |

### Medium-Impact Files (import + reference updates)

~30 files with import statement changes and variable reference updates.

### Test Files

~15 test files with fixture updates, assertion changes, and class/function renames.

---

## Verification

1. Run full CI: `make all-ci`
2. Search for any remaining "extraction" references: `rg -i "extraction" --type py`
3. Verify glossary consistency
4. Test CLI commands: `erk plan learn raw --help`

---

## Critical Files

- `packages/erk-shared/src/erk_shared/learn/` (entire module after rename)
- `packages/erk-shared/src/erk_shared/scratch/markers.py`
- `packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py`
- `src/erk/cli/commands/navigation_helpers.py`
- `docs/learned/glossary.md`