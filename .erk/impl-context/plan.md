# Plan: Rename "fix-conflicts" to "rebase" across the codebase

## Context

PR #8484 renamed the TUI-facing references from `fix_conflicts_remote` to `rebase_remote`, but the underlying CLI commands, workflow files, config keys, capabilities, and slash command still use `fix-conflicts` terminology. This creates a confusing mix where the UI says "rebase" but the commands say "fix-conflicts". Additionally, the local `erk pr fix-conflicts` command currently only acts when conflicts exist — it should always rebase (matching the remote workflow behavior).

## Scope

Three changes:
1. **Rename** all `fix-conflicts` / `fix_conflicts` references to `rebase`
2. **Behavior change**: Local command always rebases (not just when conflicts exist)
3. **Rename** the slash command `/erk:fix-conflicts` → `/erk:rebase`

## File Changes

### 1. CLI Command — rename file + behavior change
- **`src/erk/cli/commands/pr/fix_conflicts_cmd.py`** → rename to **`rebase_cmd.py`**
  - Rename function `fix_conflicts()` → `rebase()`
  - Change Click command name from `"fix-conflicts"` to `"rebase"`
  - Update docstring/help text: "Rebase PR onto base branch with AI-powered conflict resolution"
  - **Behavior change**: Remove the early exit when no conflicts. Instead, invoke the rebase-with-conflict-resolution exec script (or equivalent logic) that always rebases
  - Update `--dangerous` flag help text references
- **`src/erk/cli/commands/pr/__init__.py`**
  - Update import: `from erk.cli.commands.pr.rebase_cmd import rebase`
  - Update registration: `pr_group.add_command(rebase, name="rebase")`
- **`src/erk/cli/output.py`**
  - Rename `stream_fix_conflicts` → `stream_rebase`

### 2. Config key rename
- **`packages/erk-shared/src/erk_shared/config/schema.py`**
  - Rename `fix_conflicts_require_dangerous_flag` → `rebase_require_dangerous_flag`
  - Update `cli_key` in metadata
- **`packages/erk-shared/src/erk_shared/context/types.py`**
  - Rename field in `GlobalConfig` dataclass and factory method
- **`packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`**
  - Update `.get("fix_conflicts_require_dangerous_flag")` → `.get("rebase_require_dangerous_flag")`
  - Update `doc["fix_conflicts_..."]` assignment

### 3. Launch command rename
- **`src/erk/cli/commands/launch_cmd.py`**
  - Rename `_trigger_pr_fix_conflicts()` → `_trigger_pr_rebase()`
  - Update help text: `pr-fix-conflicts` → `pr-rebase` in all examples and descriptions
  - Update workflow dispatch: `workflow_name="pr-fix-conflicts"` → `"pr-rebase"`
  - Update status message: `"Triggering pr-fix-conflicts workflow..."` → `"Triggering pr-rebase workflow..."`
  - Update the dispatch routing: `if workflow_name == "pr-fix-conflicts":` → `"pr-rebase"`

### 4. Constants
- **`src/erk/cli/constants.py`**
  - `REBASE_WORKFLOW_NAME = "pr-rebase.yml"` (was `"pr-fix-conflicts.yml"`)
  - Update `WORKFLOW_COMMAND_MAP` key: `"pr-rebase"` (was `"pr-fix-conflicts"`)

### 5. GitHub workflow file rename
- **`.github/workflows/pr-fix-conflicts.yml`** → rename to **`pr-rebase.yml`**
  - Update `name:` field to `pr-rebase`

### 6. Capability rename
- **`src/erk/capabilities/workflows/pr_fix_conflicts.py`** → rename to **`pr_rebase.py`**
  - Rename class `PrFixConflictsWorkflowCapability` → `PrRebaseWorkflowCapability`
  - Update `name` property: `"pr-rebase-workflow"`
  - Update `description`: `"GitHub Action for rebasing PRs"`
  - Update all `.github/workflows/pr-fix-conflicts.yml` paths → `pr-rebase.yml`
  - Update `ManagedArtifact` name: `"pr-rebase"`
- **`src/erk/core/capabilities/registry.py`**
  - Update import and instantiation

### 7. TUI display command (already mostly renamed, just the display string)
- **`src/erk/tui/commands/registry.py`**
  - `_display_rebase_remote()`: change `erk launch pr-fix-conflicts` → `erk launch pr-rebase`
  - `_display_copy_rebase_remote()`: same change

### 8. Slash command rename
- **`.claude/commands/erk/fix-conflicts.md`** → rename to **`rebase.md`**
  - Update title and description to use "rebase" terminology

### 9. pyproject.toml
- Update bundled workflow path: `"pr-fix-conflicts.yml"` → `"pr-rebase.yml"` (both key and value)

### 10. .erk/state.toml
- Update artifact reference: `fix-conflicts.md` → `rebase.md`

### 11. reconcile-with-remote command (shares the dangerous flag)
- **`src/erk/cli/commands/pr/reconcile_with_remote_cmd.py`**
  - Update `fix_conflicts_require_dangerous_flag` → `rebase_require_dangerous_flag` (3 occurrences)

### 12. Tests
- **`tests/commands/pr/test_fix_conflicts.py`** → rename to **`test_rebase.py`**
  - Rename test functions, update config field references
- **`tests/commands/pr/test_fix_conflicts_remote.py`** → rename to **`test_rebase_remote.py`**
  - Update references
- **`tests/commands/pr/test_reconcile_with_remote.py`**
  - Update `fix_conflicts_require_dangerous_flag` references
- **`packages/erk-statusline/tests/test_context.py`**
  - Update `fix_conflicts_require_dangerous_flag=True` → `rebase_require_dangerous_flag=True`
- **`packages/erk-shared/tests/unit/config/test_schema.py`**
  - Update field name references
- **`tests/unit/core/test_capabilities.py`** — check for class name references

### 13. Documentation (mechanical string replacement)
Update `fix-conflicts` / `fix_conflicts` references in these docs:
- `docs/learned/cli/commands/pr-reconcile-with-remote.md`
- `docs/learned/cli/tripwires.md`
- `docs/learned/cli/command-organization.md`
- `docs/learned/cli/workflow-commands.md`
- `docs/learned/cli/local-remote-command-groups.md`
- `docs/learned/ci/workflow-naming-conventions.md`
- `docs/learned/ci/github-actions-output-patterns.md`
- `docs/learned/ci/github-cli-comment-patterns.md`
- `docs/learned/ci/containerless-ci.md`
- `docs/learned/ci/workflow-model-policy.md`
- `docs/learned/tui/action-inventory.md`
- `docs/learned/tui/view-aware-commands.md`
- `docs/learned/tui/multi-operation-tracking.md`
- `docs/learned/tui/subprocess-feedback.md`
- `docs/learned/architecture/subprocess-wrappers.md`
- `docs/learned/testing/rebase-conflicts.md`
- `docs/learned/erk/remote-workflow-template.md`
- `docs/howto/conflict-resolution.md`
- `.github/workflows/README.md`

### 14. Bundled workflow data
- **`erk/data/github/workflows/pr-fix-conflicts.yml`** → rename to **`pr-rebase.yml`** (the bundled copy)

## Verification

1. `make fast-ci` — all tests pass with renamed files/fields
2. `erk pr rebase --dangerous` — local command works (always rebases)
3. `erk launch pr-rebase --pr <N>` — remote workflow triggers correctly
4. TUI command palette shows `erk launch pr-rebase --pr <N>` for the rebase action
5. `erk config set rebase_require_dangerous_flag false` — config key works
6. `/erk:rebase` slash command loads correctly
