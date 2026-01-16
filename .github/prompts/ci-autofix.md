# Autofix CI Errors

Fix the style/formatting errors. You have full context of all CI job results.

## Job Results

- format: {{ format }}
- lint: {{ lint }}
- prettier: {{ prettier }}
- docs-check: {{ docs-check }}
- ty: {{ ty }}
- unit-tests: {{ unit-tests }} (NOT auto-fixable)
- integration-tests: {{ integration-tests }} (NOT auto-fixable)

## Errors to Fix

{{ ERRORS }}

## Rules

- For ruff format errors: run `uv run ruff format <file>` on each file
- For ruff lint errors: run `uv run ruff check --fix <file>` for auto-fixable errors
- For prettier errors: run `prettier --write <file>` for each markdown file
- For docs errors: run `make docs-sync` if generated docs are out of sync
- For ty type errors: read the files with errors, understand the type issue, and edit the files to fix the types. Run `uv run ty check` after fixing to verify.
- DO NOT attempt to fix test failures - those require human intervention
- Commit with a structured message:
  - Subject line: Brief summary of fixes (e.g., "style: fix ruff format in 2 files")
  - Blank line
  - Body explaining:
    - This was an automated commit by CI
    - Which check(s) failed (format, lint, prettier, docs)
    - What was fixed and in which files
  - Example format:

    ```
    style: fix prettier formatting in docs/

    🤖 Automated fix by CI autofix workflow

    Failed checks: prettier

    Fixed:
    - docs/learned/ci/claude-in-ci.md: markdown formatting
    - AGENTS.md: trailing whitespace
    ```

- Push the commit
