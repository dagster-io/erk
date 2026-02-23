# Plan: Use scratch storage for objective comment updates

## Context

Two objective update commands (`.claude/commands/erk/objective-update-with-landed-pr.md` and `objective-update-with-closed-plan.md`) instruct Claude to update GitHub issue comments using raw `gh api` calls with inline `-f body="..."`. When the comment body is large, Claude improvises by writing to `/tmp/objective-XXXX-body.md` instead of erk's scratch storage (`.erk/scratch/sessions/{session-id}/`). This violates the scratch storage convention and loses session-scoped auditability.

The fix: upgrade the `update_comment` gateway to support `BodyContent` (matching `update_issue_body`), create an `update-comment-body` exec script, and update the commands to use it with scratch storage.

## Step 1: Upgrade `update_comment` gateway signature

Change `body: str` to `body: BodyContent` across all 4 implementations:

- **ABC**: `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py:328` — change signature, update docstring
- **Real**: `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py:611` — handle `BodyFile` (`-F body=@{path}`) vs `BodyText` (`-f body={content}`), matching `update_issue_body` pattern at line 200
- **Fake**: `packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py:475` — resolve `BodyContent` to string before appending to `_updated_comments`
- **Dry run**: `packages/erk-shared/src/erk_shared/gateway/github/issues/dry_run.py:127` — signature-only change (no-op body)

All needed imports (`BodyContent`, `BodyFile`, `BodyText`) already exist in each file.

## Step 2: Update existing callers to use `BodyText`

4 call sites currently pass `str` — wrap in `BodyText(content=...)`:

- `src/erk/cli/commands/objective/plan_cmd.py:340` and `:405`
- `src/erk/cli/commands/exec/scripts/update_objective_node.py:503`
- `packages/erk-shared/src/erk_shared/plan_store/github.py:543` and `:550`

Add `from erk_shared.gateway.github.types import BodyText` to each file.

## Step 3: Create `update-comment-body` exec script

**New file**: `src/erk/cli/commands/exec/scripts/update_comment_body.py`

Mirror `update_issue_body.py` exactly:
- `COMMENT_ID` int argument, `--body` and `--body-file` mutually exclusive options
- Click context injection with `require_github_issues` and `require_repo_root`
- Calls `github.update_comment(repo_root, comment_id, body_arg)`
- JSON output: `{"success": true, "comment_id": N}` or `{"success": false, "error": "..."}`

## Step 4: Register in exec group

**File**: `src/erk/cli/commands/exec/group.py`

- Import: `from erk.cli.commands.exec.scripts.update_comment_body import update_comment_body` (after line 167)
- Register: `exec_group.add_command(update_comment_body, name="update-comment-body")` (after line 271)

## Step 5: Update command files

Replace raw `gh api` instructions with scratch storage + exec script in both commands:

**`objective-update-with-landed-pr.md` Step 5** (lines 106-109):
```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/
# Write the updated comment body to:
# .erk/scratch/sessions/${CLAUDE_SESSION_ID}/objective-comment-body.md
erk exec update-comment-body {comment_id} --body-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/objective-comment-body.md
```

**`objective-update-with-closed-plan.md` Step 4** (lines 85-88): Same pattern.

## Step 6: Tests

**New file**: `tests/unit/cli/commands/exec/scripts/test_update_comment_body.py`

Mirror `test_update_issue_body.py`:
- `test_update_comment_body_with_inline_body` — `--body` flag, verify `fake.updated_comments`
- `test_update_comment_body_from_file` — `--body-file` flag with `tmp_path` file
- `test_update_comment_body_fails_with_both` — both flags, exit code 1
- `test_update_comment_body_fails_without_either` — neither flag, exit code 1
- `test_update_comment_body_api_error` — gateway raises RuntimeError, verify error JSON

## Verification

1. `make fast-ci` — all existing tests pass with `BodyText` wrapping
2. New exec script tests pass
3. `erk exec update-comment-body --help` works
4. `ty` type checking passes on all modified files
