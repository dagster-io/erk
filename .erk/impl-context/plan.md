# Local Review Namespace Isolation

## Context

Reviews currently live in a flat `.erk/reviews/` directory — both bundled reviews (installed by erk capabilities like `tripwires`, `dignified-python`) and repo-specific reviews (like `audit-pr-docs`, `test-coverage`). This creates collision risk: a repo could create a file with the same name as a bundled review, silently shadowing it during `erk init`. The goal is to give repo-specific reviews their own namespace using a `local/` subdirectory, mirroring the established `.claude/commands/local/` pattern.

## Approach: `.erk/reviews/local/` subdirectory

Local (repo-specific) reviews go in `.erk/reviews/local/*.md`. Bundled reviews stay in `.erk/reviews/*.md`. Filesystem separation prevents collisions.

## Changes

### 1. `src/erk/review/parsing.py` — Discovery and parsing

**`discover_review_files()`** (line 228): Also scan `reviews_dir / "local"` subdirectory.

```python
def discover_review_files(reviews_dir: Path) -> list[Path]:
    if not reviews_dir.exists():
        return []
    files = [f for f in reviews_dir.glob("*.md") if f.is_file()]
    local_dir = reviews_dir / "local"
    if local_dir.exists():
        files.extend(f for f in local_dir.glob("*.md") if f.is_file())
    return sorted(files)
```

**`parse_review_file()`** (line 171): Add `reviews_dir` parameter to compute relative filenames. Changes `filename` from basename (`tripwires.md`) to relative path (`local/my-review.md` for local reviews, `tripwires.md` for bundled).

```python
def parse_review_file(file_path: Path, *, reviews_dir: Path) -> ReviewValidationResult:
    filename = str(file_path.relative_to(reviews_dir))
    # ... rest unchanged
```

**`discover_matching_reviews()`** (line 337): Update the `parse_review_file` call to pass `reviews_dir`:

```python
result = parse_review_file(review_file, reviews_dir=reviews_dir)
```

### 2. `src/erk/cli/commands/exec/scripts/run_review.py` — Run command (line 149)

Pass `reviews_path` to `parse_review_file`:

```python
result = parse_review_file(review_file, reviews_dir=reviews_path)
```

The `--name` flag already resolves via `reviews_path / f"{review_name}.md"`, so `--name local/my-review` correctly resolves to `.erk/reviews/local/my-review.md`. No other changes needed.

### 3. `.erk/reviews/local/` — Migrate erk's own local reviews

Move erk's repo-specific reviews into the new namespace:
- `.erk/reviews/audit-pr-docs.md` → `.erk/reviews/local/audit-pr-docs.md`
- `.erk/reviews/test-coverage.md` → `.erk/reviews/local/test-coverage.md`

### 4. `.claude/commands/local/review.md` and `code-review.md` — Update glob instructions

Update the discovery instruction from:
> Read the frontmatter of each `.erk/reviews/*.md` file

To:
> Read the frontmatter of each `.erk/reviews/*.md` and `.erk/reviews/local/*.md` file

### 5. No changes needed

- **CI workflow** (`code-reviews.yml`): `${REVIEW_NAME%.md}` correctly strips only the `.md` suffix, preserving `local/` prefix. `--name local/my-review` resolves correctly.
- **Data model** (`models.py`): `filename: str` already handles relative paths.
- **Capability system** (`review_capability.py`): Installs to `.erk/reviews/` top level only. No conflict with `local/` subdirectory.
- **Prompt assembly** (`prompt_assembly.py`): Uses `ParsedReview` data, not file paths.

## Tests

### `tests/unit/review/test_parsing.py`

- `TestDiscoverReviewFiles`: Add test that discovers files in both `reviews_dir/*.md` and `reviews_dir/local/*.md`
- `TestParseReviewFile`: Update calls to pass `reviews_dir` kwarg; add test verifying `filename` is `local/foo.md` for local reviews
- `TestDiscoverMatchingReviews`: Add test with a local review in `local/` subdirectory

### `tests/unit/cli/commands/exec/scripts/test_discover_reviews.py`

- Add test with a local review file in `local/` subdirectory, verify it appears in discovery output with `filename: "local/my-review.md"` and matrix entry

### `tests/unit/cli/commands/exec/scripts/test_run_review.py`

- Add test with `--name local/my-review` resolving to `.erk/reviews/local/my-review.md`

## Verification

1. Run unit tests: `uv run pytest tests/unit/review/test_parsing.py tests/unit/cli/commands/exec/scripts/test_discover_reviews.py tests/unit/cli/commands/exec/scripts/test_run_review.py`
2. Verify erk's own local reviews work: `erk exec run-review --name local/audit-pr-docs --local --dry-run`
3. Verify bundled reviews still work: `erk exec run-review --name tripwires --local --dry-run`
