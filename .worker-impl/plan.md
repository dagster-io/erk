# Plan: Auto-fix Python formatting in CI

## Context
The prettier workflow already auto-formats markdown and commits changes. We want the same for Python formatting with ruff.

## Current State
- `.github/workflows/format.yml` runs `make format-check` which fails if formatting is wrong
- `.github/workflows/prettier.yml` runs `make prettier` and auto-commits with `git-auto-commit-action`

## Change
Modify `.github/workflows/format.yml` to auto-format and commit, matching the prettier pattern.

## File to Modify
- `.github/workflows/format.yml`

## Changes

1. Change `permissions: contents: read` → `contents: write`
2. Replace step "Check Python formatting" with:
   - Run `make format` (formats files, doesn't just check)
   - Add git-auto-commit-action step

## Target State

```yaml
permissions:
  contents: write

# ... in the format job steps:
    - name: Format Python files
      run: make format
    - name: Commit formatting changes
      uses: stefanzweifel/git-auto-commit-action@v5
      with:
        commit_message: "style: auto-format Python with ruff"
        file_pattern: "*.py **/*.py"
```