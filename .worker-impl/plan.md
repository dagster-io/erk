# Plan: Decompose `make publish` into `make prepare` and `make publish`

## Enrichment Details

### Process Summary

- **Mode**: enriched
- **Guidance applied**: yes (user clarifications changed approach from flags to separate commands)
- **Guidance text**: N/A (no explicit guidance provided, but clarifying questions refined approach)
- **Questions asked**: 3
- **Context categories extracted**: 6 of 8

### Clarifications Made

1. **State detection approach**: User selected "Separate command" - Create distinct `erk-dev publish-release` command for the publish-only step. This changes the implementation from adding `--skip-prepare` flag to creating a new command.

2. **Validation timing**: User selected "Always validate" - Run all validation in prepare phase to fail early before any changes are made.

3. **Missing artifacts behavior**: User selected "Error and exit" - Exit with clear error message directing user to run `make prepare` first rather than falling through to full workflow.

### Context Categories Populated

- API/Tool Quirks
- Architectural Insights
- Domain Logic & Business Rules
- Raw Discoveries Log
- Planning Artifacts
- Implementation Risks

---

## Goal

Split the publishing workflow into two separate Make targets with corresponding separate erk-dev commands:
- `make prepare` -> `erk-dev prepare-release`: Bump versions, sync dependencies, build artifacts (committable state)
- `make publish` -> `erk-dev publish-release`: Upload to PyPI and push to remote (requires prior prepare)

This allows the user to review and manually commit version changes before publishing to PyPI.

## Current State

The current `make publish` target calls `erk-dev publish-to-pypi`, which performs the entire workflow in one shot:

1. **PREPARE phase** (lines 463-508 in command.py):
   - Repository validation (branch sync, uncommitted changes)
   - Git pull
   - Package discovery (dot-agent-kit, erk)
   - Version consistency check
   - Version bump (patch increment)
   - Version synchronization across all packages (pyproject.toml, version.py)
   - Dependency update (uv sync)
   - Build packages (creates dist/ artifacts)
   - Artifact validation

2. **PUBLISH phase** (lines 510-516 in command.py):
   - Publish to PyPI (uvx uv-publish)
   - Commit changes (version files, uv.lock)
   - Push to remote

## Revised Implementation Approach

**Strategy: Separate erk-dev commands**

Based on clarifications, create two distinct commands:
- `erk-dev prepare-release`: Executes prepare phase only
- `erk-dev publish-release`: Executes publish phase only, requires prepared state

**Rationale:**
- Cleaner separation of concerns
- Each command independently testable
- Explicit user intent rather than flag-based mode switching
- Existing `erk-dev publish-to-pypi` can be deprecated or retained for backward compatibility

### Implementation Steps

1. **Create `erk-dev prepare-release` command**
   - Location: `packages/erk-dev/src/erk_dev/commands/prepare_release/command.py`
   - Extract prepare logic from publish_to_pypi/command.py (lines 463-508)
   - Include ALL validation (branch sync, uncommitted changes) - fail early
   - Run git pull
   - Discover packages, validate version consistency
   - Bump patch version, synchronize across packages
   - Run uv sync
   - Build all packages to dist/
   - Validate artifacts exist
   - Exit with success message (do NOT commit, publish, or push)

2. **Create `erk-dev publish-release` command**
   - Location: `packages/erk-dev/src/erk_dev/commands/publish_release/command.py`
   - Requires dist/ artifacts to exist with correct version
   - Validate artifacts exist for expected version (read from pyproject.toml)
   - If artifacts missing or version mismatch: error and exit with message to run `make prepare`
   - Publish all packages to PyPI (uvx uv-publish)
   - Push to remote (git push)
   - Do NOT commit (user already committed manually after prepare)

3. **Extract shared utilities**
   - Location: `packages/erk-dev/src/erk_dev/commands/publish_to_pypi/shared.py` (or `utils.py`)
   - Move reusable functions from command.py:
     - `run_command()`
     - `get_workspace_packages()`
     - `get_current_version()`
     - `validate_build_artifacts()`
     - `publish_package()`, `publish_all_packages()`
     - `ensure_branch_is_in_sync()`
     - etc.
   - Import shared utilities into both new commands

4. **Update Makefile with new targets**
   - Add `prepare` target: calls `erk-dev prepare-release`
   - Update `publish` target: calls `erk-dev publish-release`
   - Retain or deprecate existing `publish` that called `publish-to-pypi`
   - Update comments to document the split workflow

5. **Register new commands in CLI**
   - Location: `packages/erk-dev/src/erk_dev/cli.py`
   - Import and register `prepare_release_command`
   - Import and register `publish_release_command`

6. **Add tests for new commands**
   - Test `prepare-release` validates and builds without committing/publishing
   - Test `publish-release` fails when artifacts missing
   - Test `publish-release` succeeds when artifacts exist with matching version
   - Test error messages guide user correctly

## Expected Workflow

### Current (single-phase):
```bash
make publish  # Does everything: prepare -> publish -> commit -> push
```

### New (two-phase):
```bash
make prepare           # Bump versions, build artifacts (validates first)
# Review changes in git diff
git add -A && git commit -m "Bump version to X.Y.Z"
make publish           # Upload to PyPI, push (requires artifacts exist)
```

### Error case (missing prepare):
```bash
make publish           # Without prior prepare
# Error: No artifacts found in dist/ for version X.Y.Z
# Run 'make prepare' first to bump version and build packages
```

## Files to Create

1. **`packages/erk-dev/src/erk_dev/commands/prepare_release/__init__.py`**
   - Optional, may contain docstring or be empty

2. **`packages/erk-dev/src/erk_dev/commands/prepare_release/command.py`**
   - `prepare_release_command()` Click command
   - Prepare phase logic (validation, version bump, build)

3. **`packages/erk-dev/src/erk_dev/commands/publish_release/__init__.py`**
   - Optional, may contain docstring or be empty

4. **`packages/erk-dev/src/erk_dev/commands/publish_release/command.py`**
   - `publish_release_command()` Click command
   - Publish phase logic (artifact validation, PyPI upload, push)

## Files to Modify

1. **`packages/erk-dev/src/erk_dev/commands/publish_to_pypi/command.py`**
   - Extract shared utilities to separate module
   - May retain for backward compatibility or deprecate

2. **`packages/erk-dev/src/erk_dev/cli.py`**
   - Add imports for new commands
   - Register with `cli.add_command()`

3. **`Makefile`**
   - Add `prepare` target
   - Update `publish` target to use `publish-release`
   - Update `.PHONY` declaration

## Context & Understanding

### API/Tool Quirks

- **PyPI propagation delay**: The constant `PYPI_PROPAGATION_WAIT_SECONDS = 5` accounts for CDN propagation. When publishing multiple packages, there's a 5-second wait between packages to ensure dependency availability.

- **uv-publish invocation**: Uses `uvx uv-publish` not `uv publish`. The artifacts are passed directly as arguments to the command.

- **Artifact naming normalization**: Package names like `dot-agent-kit` become `dot_agent_kit` in artifact filenames (wheel and sdist). The `normalize_package_name()` function handles this.

- **Git status parsing quirk**: Lines shorter than 4 characters are filtered out. The format is "XY filename" where XY is 2-char status code + space.

### Architectural Insights

- **Workspace packages are hardcoded**: The `get_workspace_packages()` function returns a fixed list of `dot-agent-kit` and `erk`. No dynamic discovery.

- **Version synchronization pattern**: Versions are updated in both `pyproject.toml` AND `version.py` files. The version.py path follows the pattern: `{pkg.path}/src/{pkg.name.replace('-','_')}/version.py`

- **Excluded files in git status check**: The files `pyproject.toml`, `uv.lock`, and `packages/dot-agent-kit/pyproject.toml` are excluded from uncommitted changes check because the publish workflow modifies them.

- **Click command naming convention**: Function must be named `{command_name}_command` (e.g., `publish_to_pypi_command`). This is required for the static import pattern in cli.py.

- **Dependency order matters**: Packages are published in the order returned by `get_workspace_packages()`: `dot-agent-kit` first, then `erk`. This ensures dependencies are available on PyPI before dependents.

### Domain Logic & Business Rules

- **Branch must track upstream**: Publishing is blocked if the branch doesn't track a remote upstream. User must run `git push -u origin <branch>` first.

- **Branch must be in sync**: If local branch is behind upstream, publishing is blocked. User must reconcile with `git pull --rebase`.

- **Version consistency required**: All packages must have the same version before bumping. Mismatch causes failure.

- **Only patch version bumping**: The `bump_patch_version()` function only increments the patch number (X.Y.Z -> X.Y.Z+1). No support for minor/major bumps.

- **git pull is mandatory**: The prepare phase always runs `git pull` to ensure working with latest code.

- **Commit message format**: Uses Claude Code attribution format with emoji and Co-Authored-By header.

### Raw Discoveries Log

- Command is in `packages/erk-dev/src/erk_dev/commands/publish_to_pypi/command.py`
- Uses Click for CLI, not argparse
- Has `--dry-run` flag that shows what would be done
- Uses `user_output()` for all user-facing messages (from `erk_dev.cli.output`)
- Build artifacts go to `dist/` directory at repo root
- Tests exist in `packages/erk-dev/tests/test_publish_to_pypi.py` - focus on git status parsing
- Makefile has `build` target that also creates dist/ (cleans first, builds both packages)
- `run_pep723_script()` is a compatibility shim for tests

### Planning Artifacts

**Files examined:**
- `/Users/schrockn/code/erk/packages/erk-dev/src/erk_dev/commands/publish_to_pypi/command.py` (full file, 537 lines)
- `/Users/schrockn/code/erk/Makefile` (full file, 106 lines)
- `/Users/schrockn/code/erk/packages/erk-dev/tests/test_publish_to_pypi.py` (full file, 153 lines)

**Commands run:**
- `find` to locate publish-related test files
- `git log` to check recent history of publish command

**Key line references:**
- Lines 463-508: Prepare phase (validation, version bump, build)
- Lines 510-516: Publish phase (PyPI upload, commit, push)
- Lines 388-432: `commit_changes()` function
- Lines 341-358: `publish_package()` function

### Implementation Risks

- **Shared code extraction**: Moving utilities to a shared module requires updating imports in existing code and tests. Risk of breaking existing `publish-to-pypi` command.

- **Version detection in publish-release**: The publish-release command needs to read version from pyproject.toml to validate artifacts. If user modified pyproject.toml after prepare but before publish, version mismatch could occur.

- **No rollback mechanism**: If publish-release fails partway through (e.g., first package succeeds, second fails), there's no automatic rollback. Manual intervention required.

- **Test coverage gap**: Existing tests only cover git status parsing. No integration tests for the full workflow. New commands should have better test coverage.

- **Backward compatibility**: If `publish-to-pypi` is kept, users might use the old single-phase workflow accidentally. Consider deprecation warning or removal.
