# Plan: Review Exclude List for Vendored/Imported Python

## Context

PR #8758 (skill-creator) has 16 bot review comments all targeting imported Python files under `.claude/skills/skill-creator/`. These files are vendored/imported code that we don't want to enforce our coding standards on. Ruff and ty already exclude `.claude/skills/` — the review system needs the same capability.

**Goal**: Add a `[tool.erk.reviews]` section to `pyproject.toml` with an `exclude` list of gitignore-style globs, applied at two points so review bots never see excluded files.

## Approach

### 1. Add config to pyproject.toml

```toml
[tool.erk.reviews]
exclude = [".claude/skills/"]
```

### 2. Add config reader: `src/erk/review/config.py` (new file)

Read `[tool.erk.reviews].exclude` from `pyproject.toml` using `tomllib` (already used in `src/erk/cli/config.py`). Return `tuple[str, ...]` of exclude globs. Return empty tuple if section/key missing or file doesn't exist.

### 3. Filter changed_files in discovery: `src/erk/review/parsing.py`

In `discover_matching_reviews()`, accept an optional `exclude_patterns: tuple[str, ...]` parameter. Before matching reviews against files, filter `changed_files` through a pathspec built from exclude patterns. This prevents reviews from triggering when only excluded files changed.

Add a helper `_is_excluded(filename, exclude_spec)` or just build the pathspec once and filter inline.

### 4. Wire config into discovery caller: `src/erk/cli/commands/exec/scripts/discover_reviews.py`

Read the exclude config from `pyproject.toml` at `cwd` and pass it to `discover_matching_reviews()`.

### 5. Inject exclude instruction into review prompt: `src/erk/review/prompt_assembly.py`

Add an `exclude_patterns` parameter to `assemble_review_prompt()`. When non-empty, inject a section into both prompt templates (after "Get the Diff" step) telling the review bot to skip files matching exclude patterns:

```
## File Exclusions

The following file patterns are excluded from review. Do NOT post inline comments
or flag violations for files matching these patterns:
{exclude_patterns}
```

### 6. Wire config into prompt assembly caller: `src/erk/cli/commands/exec/scripts/run_review.py`

Read the exclude config and pass to `assemble_review_prompt()`.

### 7. Tests

- `tests/unit/review/test_config.py` — Test reading exclude from pyproject.toml (present, missing, empty)
- `tests/unit/review/test_parsing.py` — Add test for `discover_matching_reviews` with exclude patterns filtering changed_files
- `tests/unit/review/test_prompt_assembly.py` — Test that exclude patterns appear in assembled prompt (if tests exist for prompt assembly; check first)
- `tests/unit/cli/commands/exec/scripts/test_discover_reviews.py` — May need update if the CLI wiring changes significantly

## Files to Modify

| File | Action |
|------|--------|
| `pyproject.toml` | Add `[tool.erk.reviews]` section |
| `src/erk/review/config.py` | **New** — read exclude config |
| `src/erk/review/parsing.py` | Add exclude filtering to `discover_matching_reviews` |
| `src/erk/review/prompt_assembly.py` | Add exclude instruction injection |
| `src/erk/cli/commands/exec/scripts/discover_reviews.py` | Wire config reading |
| `src/erk/cli/commands/exec/scripts/run_review.py` | Wire config reading |
| `tests/unit/review/test_config.py` | **New** — config reader tests |
| `tests/unit/review/test_parsing.py` | Add exclude filtering test |

## Verification

1. Run unit tests: `pytest tests/unit/review/`
2. Run discover-reviews dry run: `erk exec discover-reviews --pr-number 8758` and verify `.claude/skills/` files don't trigger reviews
3. Run review dry run: `erk exec run-review --name dignified-python --pr-number 8758 --dry-run` and verify exclude instruction in prompt
4. Run `make fast-ci` to verify no regressions
