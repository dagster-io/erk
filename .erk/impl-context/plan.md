# Plan: Split AI Generation Out of `erk pr submit`

## Context

`erk pr submit` internally calls Claude (via `CommitMessageGenerator` → `ctx.prompt_executor`) to generate PR title and body. When invoked from a Claude Code skill, this creates a nested Claude API call that runs as an opaque subprocess — taking 9+ minutes with zero progress visibility, confusing the agent and blocking the session.

The fix: give the agent two `erk exec` commands to bookend the AI step, so the agent generates the description natively (no subprocess) and a thin exec command applies the result.

## New Flow (in `/erk:pr-submit` skill)

```
erk pr submit --skip-description       # git/graphite ops only — no AI
erk exec get-pr-context                # agent reads diff + plan + commits
[agent generates title + body]
erk exec set-pr-description --title "..." --body "..."  # applies result to PR
```

## Changes

### 1. `erk pr submit --skip-description` flag

**File:** `src/erk/cli/commands/pr/submit_cmd.py` (add `--skip-description` option)
**File:** `src/erk/cli/commands/pr/submit_pipeline.py` (pass flag through `SubmitState`, skip phases 4-5)

When `--skip-description` is set, the pipeline executes phases 1-3 (push + create PR + PR footer) then exits early — skipping `generate_description` and the PR title/body update in `finalize_pr`. The PR gets created with a placeholder title (branch name or first commit subject) and empty body.

### 2. `erk exec get-pr-context` (new)

**File:** `src/erk/cli/commands/exec/scripts/get_pr_context.py`

Outputs JSON to stdout:
```json
{
  "branch": { "current": "plnd/...", "parent": "master" },
  "pr": { "number": 7930, "url": "https://..." },
  "diff_file": "/tmp/pr-diff-xxx.diff",
  "commit_messages": ["msg1", "msg2"],
  "plan_context": {
    "plan_id": "7930",
    "plan_content": "# Plan...",
    "objective_summary": null
  }
}
```

Implementation reuses:
- `discover_branch_context(ctx, cwd)` → `src/erk/cli/commands/pr/shared.py`
- `ctx.github.get_pr_for_branch()` → get PR number/URL
- `run_diff_extraction(ctx, ...)` → writes diff to temp file, returns `Path`
- `PlanContextProvider(ctx.plan_backend, ctx.github_issues).get_plan_context()` → `src/erk/core/plan_context_provider.py`
- `ctx.git.commit.get_commit_messages_since(cwd, parent_branch)`

No `--session-id` needed (uses `uuid.uuid4()` internally for diff file isolation).

### 3. `erk exec set-pr-description --title "..." --body "..."` (new)

**File:** `src/erk/cli/commands/exec/scripts/set_pr_description.py`

Takes `--title` and `--body` (and optional `--body-file` for large bodies) and updates the PR with proper metadata assembly.

Implementation reuses:
- `discover_branch_context(ctx, cwd)` → branch/PR discovery
- `ctx.github.get_pr_for_branch()` → get existing PR body for header/footer extraction
- `discover_issue_for_footer(impl_dir, branch_name, existing_body, plans_repo)` → `src/erk/cli/commands/pr/shared.py`
- `extract_header_from_body(existing_body)` → `erk_shared.gateway.github.pr_footer`
- `extract_metadata_prefix(existing_body)` → `erk_shared.plan_store.draft_pr_lifecycle` (for draft-PR backend)
- `assemble_pr_body(body, plan_context, pr_number, issue_number, plans_repo, header, metadata_prefix)` → `src/erk/cli/commands/pr/shared.py`
- `ctx.github.update_pr_title_and_body()` → write result

Note: This command does NOT call Claude. It takes agent-generated title/body as arguments.

### 4. Register new commands

**File:** `src/erk/cli/commands/exec/__init__.py`
Add both new commands to the exec group.

### 5. Update `/erk:pr-submit` skill

**File:** `.claude/commands/erk/pr-submit.md`

Replace the single `erk pr submit` call with the three-step flow. The skill now:
1. Runs `erk pr submit --skip-description` (git/graphite only)
2. Calls `erk exec get-pr-context`, reads the JSON output
3. Reads the diff file path from JSON and scans the diff
4. Generates title + body (natively, as the running agent — no subprocess)
5. Calls `erk exec set-pr-description --title "..." --body "..."`
6. Reports PR URL and success

### 6. Tests

**Files to create:**
- `tests/unit/cli/commands/exec/scripts/test_get_pr_context.py`
- `tests/unit/cli/commands/exec/scripts/test_set_pr_description.py`

Test pattern: `CliRunner` + `FakeGit` + `FakeGitHub` + `FakeGitHubIssues` injected via `build_workspace_test_context()` (same pattern as `test_update_pr_description.py`).

Key test cases for `get-pr-context`:
- Happy path: outputs valid JSON with all fields
- No PR found: exits 1 with clear error
- No plan context: `plan_context` is null in output

Key test cases for `set-pr-description`:
- Happy path: PR title + body updated, header/footer preserved
- Draft-PR mode: metadata prefix preserved
- Issue mismatch: exits 1 with error

## Verification

```bash
# Unit tests
make fast-ci

# Manual smoke test (in a worktree with a plan branch + PR)
erk pr submit --skip-description
erk exec get-pr-context  # verify JSON output
erk exec set-pr-description --title "Test title" --body "Test body"
# Check PR on GitHub: title/body updated, footer preserved
```
