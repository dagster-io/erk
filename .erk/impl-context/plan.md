# Plan: Archive MkDocs Site and Consolidate Docs Targets

## Context

The project is transitioning from MkDocs to Astro/Starlight (`docs-site/`). The mkdocs source content currently lives in `docs/` alongside non-mkdocs content (`learned/`, `developer/`, `user/`, `public-content/`). This change archives the mkdocs content, removes mkdocs infrastructure, and makes `docs-site` the primary documentation target.

## Steps

### 1. Move mkdocs source content to `docs-site-archived/`

Move these from `docs/` to `docs-site-archived/`:
- `contributing/`
- `faq/`
- `howto/`
- `index.md`
- `ref/`
- `stylesheets/`
- `TAO.md`
- `topics/`
- `tutorials/`

Move `mkdocs.yml` to `docs-site-archived/mkdocs.yml`

**Remains in `docs/`:** `learned/`, `developer/`, `user/`, `public-content/`

### 2. Update Makefile

**Remove these mkdocs targets:**
- `docs` (line 159-160): `uv run mkdocs build`
- `docs-serve` (line 162-163): `uv run mkdocs serve`
- `docs-deploy` (line 165-166): `uv run mkdocs gh-deploy --force`

**Rename docs-site targets to primary docs targets:**
- `docs-site-build` → `docs` (cd docs-site && npm install && npm run build)
- `docs-site-serve` → `docs-serve` (cd docs-site && npm install && npm run dev)

**Update .PHONY line** (line 1): remove `docs-deploy`, rename `docs-site-build`/`docs-site-serve` to `docs`/`docs-serve`

### 3. Remove mkdocs CI workflow

Delete `.github/workflows/docs.yml`

Update `.github/workflows/README.md`:
- Remove the `docs.yml` row from the workflow table (line 48)

### 4. Remove mkdocs dependencies from pyproject.toml

Remove from dev dependencies (lines 52-53):
- `mkdocs>=1.6.0`
- `mkdocs-material>=9.5.0`

### 5. Update .gitignore

Change:
```
# MkDocs build output
site/
```
To:
```
# Archived MkDocs build output
docs-site-archived/site/
```

### 6. Update docs/contributing/writing-documentation.md

This file references MkDocs on line 118. Update or note that the project now uses Astro/Starlight.

## Files Modified

- `Makefile` - Remove mkdocs targets, rename docs-site targets
- `.github/workflows/docs.yml` - Delete
- `.github/workflows/README.md` - Remove docs.yml row
- `pyproject.toml` - Remove mkdocs deps
- `.gitignore` - Update site/ reference
- `docs/contributing/writing-documentation.md` - Update MkDocs reference
- `mkdocs.yml` - Move to `docs-site-archived/`
- `docs/{contributing,faq,howto,ref,stylesheets,topics,tutorials}/` - Move to `docs-site-archived/`
- `docs/index.md`, `docs/TAO.md` - Move to `docs-site-archived/`

## Verification

1. `ls docs/` - should only contain: `learned/`, `developer/`, `user/`, `public-content/`
2. `ls docs-site-archived/` - should contain all mkdocs content + mkdocs.yml
3. `make docs` - should run the Astro/Starlight build (cd docs-site && npm install && npm run build)
4. `make docs-serve` - should run the Astro/Starlight dev server
5. `grep -r mkdocs Makefile` - should return nothing
6. Verify no broken references to moved files in the rest of the codebase
