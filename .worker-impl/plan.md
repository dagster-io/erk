# Plan: Migrate `erk pr update-description` to `erk exec update-pr-description`

## Context

`erk pr update-description` is only called from one place: the `/erk:pr-address` skill (line 286). It's an agent-facing utility, not a human workflow — humans use `erk pr rewrite` which does the full squash + push + update cycle. Demoting it to an exec command removes it from the user-facing `erk pr` help and puts it where it belongs: alongside other agent-facing exec commands like `generate-pr-summary`, `resolve-review-threads`, etc.

## Approach

The new exec command will use `require_*()` context helpers and reuse shared functions from `pr/shared.py`. Those shared functions take `ErkContext`, which we obtain via `require_context(ctx)`.

## Steps

### 1. Create exec script

**File:** `src/erk/cli/commands/exec/scripts/update_pr_description.py`

- Port logic from `update_description_cmd.py`
- Use `@click.pass_context` with `require_context(ctx)` to get `ErkContext`
- Reuse shared functions: `discover_branch_context`, `run_diff_extraction`, `run_commit_message_generation`, `assemble_pr_body`, `echo_plan_context_status`, `cleanup_diff_file`, `require_claude_available`, `discover_issue_for_footer`
- Keep same options: `--debug`, `--session-id`
- Model after `generate_pr_summary.py` for exec command structure

### 2. Register in exec group

**File:** `src/erk/cli/commands/exec/group.py`

- Import `update_pr_description` from new script
- Add `exec_group.add_command(update_pr_description, name="update-pr-description")`

### 3. Remove from PR group

**File:** `src/erk/cli/commands/pr/__init__.py`

- Remove import of `pr_update_description`
- Remove `pr_group.add_command(pr_update_description, name="update-description")`

### 4. Delete old command file

**File:** `src/erk/cli/commands/pr/update_description_cmd.py` — delete

### 5. Update skill call site

**File:** `.claude/commands/erk/pr-address.md` (line 286)

- Change `erk pr update-description --session-id "${CLAUDE_SESSION_ID}"` to `erk exec update-pr-description --session-id "${CLAUDE_SESSION_ID}"`

### 6. Move and adapt tests

- **Delete:** `tests/commands/pr/test_update_description.py`
- **Create:** `tests/unit/cli/commands/exec/scripts/test_update_pr_description.py`
- Adapt to invoke the exec command directly (not through `pr_group`)
- Keep the same test cases and fakes

## Verification

- Run tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_update_pr_description.py`
- Run ty: `uv run ty check src/erk/cli/commands/exec/scripts/update_pr_description.py`
- Verify old command is gone: `uv run pytest tests/commands/pr/test_update_description.py` should not exist
- Grep for stale references: `rg "pr update-description" --type md --type py`