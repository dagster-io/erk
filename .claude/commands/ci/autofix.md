# CI Autofix

Run CI checks and fix auto-fixable failures iteratively. Designed for GitHub Actions via `claude --print`.

## CI Pipeline

Run these checks (same as `make fast-ci`):

1. **lint** - `uv run ruff check .`
2. **format-check** - `uv run ruff format --check .`
3. **prettier-check** - `prettier --check '**/*.md' --ignore-path .gitignore`
4. **md-check** - `make md-check`
5. **docs-validate** - `make docs-validate`
6. **docs-sync-check** - `make docs-sync-check`
7. **ty** - `uv run ty`
8. **test** - `uv run pytest tests/`

## Auto-Fix Commands

| Check           | Fix Command                                           |
| --------------- | ----------------------------------------------------- |
| lint            | `uv run ruff check --fix .`                           |
| format-check    | `uv run ruff format .`                                |
| prettier-check  | `prettier --write '**/*.md' --ignore-path .gitignore` |
| docs-sync-check | `make docs-sync`                                      |
| docs-validate   | `make docs-sync`                                      |
| md-check        | Write `@AGENTS.md` to any failing CLAUDE.md file      |

## Not Auto-Fixable

Stop and report if these fail (require manual intervention):

- **ty** - Type errors
- **test** - Test failures

## Workflow

1. Run `make fast-ci`
2. If auto-fixable check fails, apply the fix command
3. Re-run `make fast-ci`
4. Repeat until passing or stuck on non-auto-fixable issue
5. If all checks pass, commit and push:
   ```bash
   git add -A
   git commit -m "style: auto-fix CI errors"
   git push
   ```

## Limits

- Maximum 5 iterations
- Stop if same error persists after 2 attempts
- Stop immediately on non-auto-fixable failures

## Note

This command runs Bash directly (no devrun agents) for use in `claude --print` mode.
