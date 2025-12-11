# Plan: Refactor test_submit.py to Use Fakes Instead of Mocks

## Problem

The tests in `tests/commands/pr/test_submit.py` use `@patch` decorators to mock internal functions (`execute_core_submit`, `execute_diff_extraction`, `execute_graphite_enhance`, `execute_finalize`). This violates the fake-driven testing architecture.

## Reference Implementation

The correct pattern is demonstrated in `packages/erk-shared/tests/unit/integrations/pr/test_submit.py` which tests `execute_core_submit` properly using fakes.

## Files to Modify

1. `tests/commands/pr/test_submit.py` - Remove all `@patch` decorators, use fakes

## Required Fake Configurations

For `execute_core_submit` to succeed:

```python
git = FakeGit(
    current_branches={tmp_path: "feature-branch"},
    repository_roots={tmp_path: tmp_path},
    trunk_branches={tmp_path: "main"},  # or default_branches
    commits_ahead={(tmp_path, "main"): 2},  # Must be > 0
)
github = FakeGitHub(
    authenticated=True,  # For auth check
    pr_diffs={999: "diff content"},  # 999 is default PR number from create_pr
)
```

For `execute_diff_extraction` to succeed:

```python
# Needs pr_diffs configured in FakeGitHub
github = FakeGitHub(pr_diffs={pr_number: "diff content"})
```

For `execute_graphite_enhance` to skip (no Graphite tracking):

```python
graphite = FakeGraphite(authenticated=True)  # No branches configured = skipped
```

## Implementation Steps

### Step 1: Remove mock imports and decorators

Remove:

```python
from unittest.mock import Mock, patch
```

Remove all `@patch("erk.cli.commands.pr.submit_cmd...")` decorators.

### Step 2: Refactor each test

#### `test_pr_submit_fails_when_claude_not_available`

- Already correct - uses FakeClaudeExecutor

#### `test_pr_submit_fails_when_core_submit_returns_error`

```python
def test_pr_submit_fails_when_core_submit_returns_error() -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.git_dir},
        )
        github = FakeGitHub(authenticated=False)  # <- Auth failure triggers error
        claude_executor = FakeClaudeExecutor(claude_available=True)
        ctx = build_workspace_test_context(env, git=git, github=github, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "not authenticated" in result.output
```

#### `test_pr_submit_fails_when_diff_extraction_fails`

- Configure `FakeGitHub` without `pr_diffs` entry (empty dict)
- Real `execute_diff_extraction` will fail

#### `test_pr_submit_fails_when_commit_message_generation_fails`

- Configure full success path for core_submit and diff_extraction
- Use `FakeClaudeExecutor(simulated_prompt_error=...)` to fail message gen

#### `test_pr_submit_fails_when_finalize_fails`

- Configure `FakeGitHub(pr_update_should_succeed=False)`

#### `test_pr_submit_success`

```python
def test_pr_submit_success(tmp_path: Path) -> None:
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature"},
            repository_roots={env.cwd: env.git_dir},
            trunk_branches={env.git_dir: "main"},
            commits_ahead={(env.cwd, "main"): 2},
        )
        github = FakeGitHub(
            authenticated=True,
            pr_diffs={999: "diff --git a/file.py..."},  # 999 is default from FakeGitHub.create_pr
        )
        graphite = FakeGraphite(authenticated=True)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add awesome feature\n\nThis PR adds a feature.",
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        assert len(github.created_prs) == 1  # PR was created
        assert len(github.updated_pr_titles) == 1  # Title was updated
        assert len(claude_executor.prompt_calls) == 1  # AI was called
```

#### `test_pr_submit_with_no_graphite_flag`

- Same as success test
- Verify `graphite.submit_stack_calls` is empty with `--no-graphite`

### Step 3: Handle scratch directory

The `write_scratch_file` function writes to `repo_root/.tmp/<session-id>/`. Ensure the test directory structure supports this.

## Mutation Tracking Properties for Assertions

| Property                       | Tracks                                          |
| ------------------------------ | ----------------------------------------------- |
| `github.created_prs`           | PR creations (branch, title, body, base, draft) |
| `github.updated_pr_titles`     | Title updates (pr_number, title)                |
| `github.updated_pr_bodies`     | Body updates (pr_number, body)                  |
| `git._pushed_branches`         | Push operations (remote, branch, set_upstream)  |
| `graphite.submit_stack_calls`  | Graphite submit calls                           |
| `claude_executor.prompt_calls` | Claude prompts                                  |

## Success Criteria

- All `@patch` decorators removed
- All `Mock` types removed
- Tests use constructor injection for fake configuration
- Assertions use mutation tracking properties
- All tests pass: `uv run pytest tests/commands/pr/test_submit.py -v`
