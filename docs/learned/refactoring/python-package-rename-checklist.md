---
title: Python Package Rename Checklist
read_when:
  - "renaming a Python package or module"
  - "performing a large-scale rename across a monorepo"
tripwires:
  - action: "renaming a Python package without checking all entry points"
    warning: "Package renames require updating pyproject.toml scripts, Makefile targets, CI config, and documentation. Use the checklist in python-package-rename-checklist.md."
  - action: "verifying a CLI entry point with --help without checking if it uses Click or argparse"
    warning: "Check whether the CLI uses Click or argparse before running --help. Click commands print help and exit 0; argparse may behave differently. For uv-managed packages, use 'uv run <name> --help'."
    score: 5
---

# Python Package Rename Checklist

Reference checklist derived from the erk-slack-bot to erkbot rename (PR history). Use this when renaming any Python package in a monorepo.

## Checklist

1. **pyproject.toml** — Update `[project]` name, `[project.scripts]` entry points, and `[tool.uv.sources]` references in both the package's own pyproject.toml and the root pyproject.toml
2. **Directory rename** — Rename `packages/old-name/src/old_name/` to `packages/new-name/src/new_name/`
3. **Import updates** — Update all `from old_name import ...` and `import old_name` across the codebase
4. **CLI entry points** — Update `[project.scripts]` to point to the new module path
5. **Makefile targets** — Update any targets that reference the old package name (e.g., `make run-old-name` -> `make run-new-name`)
6. **CI configuration** — Update `.github/workflows/` files that reference the old package path or name
7. **Documentation references** — Update docs that reference the old name, including `docs/learned/` files
8. **Test imports** — Update test files under `packages/new-name/tests/` to use new import paths
9. **Lock file** — Run `uv sync` to regenerate the lock file with the new package name
10. **Verify CLI entry point** — Run `uv run new-name --help` to confirm the entry point resolves correctly

## Key Lessons

- **Entry point verification is easy to miss**: The CLI entry point in pyproject.toml `[project.scripts]` must point to the renamed module, not just the renamed package directory
- **Monorepo cross-references**: In a uv workspace, other packages may have `[tool.uv.sources]` entries pointing to the old package path
- **CI may reference package paths directly**: GitHub Actions workflows sometimes hardcode paths like `packages/old-name/`
