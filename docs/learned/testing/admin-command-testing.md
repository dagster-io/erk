---
title: Admin Command Testing Patterns
last_audited: "2026-02-11 00:00 PT"
audit_result: clean
read_when:
  - "writing tests for admin CLI commands"
  - "using FakeGitHubAdmin in tests"
  - "testing permission-related CLI commands"
tripwires:
  - action: "testing admin commands that read GitHub settings"
    warning: "Use FakeGitHubAdmin with workflow_permissions dict to configure read state. Do not mock subprocess calls."
---

# Admin Command Testing Patterns

Testing patterns for `erk admin` subcommands using the fake-driven architecture.

## FakeGitHubAdmin Setup

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py, FakeGitHubAdmin -->

`FakeGitHubAdmin` accepts keyword arguments to configure initial state:

```python
from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin

admin = FakeGitHubAdmin(
    workflow_permissions={"can_approve_pull_request_reviews": True},
)
```

Default state (no arguments): permissions with `can_approve_pull_request_reviews: False` and auth status of authenticated user "testuser".

## Testing Display vs Mutation Modes

**Display mode** (read-only): Configure `workflow_permissions` in the constructor, then assert command output reflects the configured state.

See `test_display_mode_shows_enabled()` and `test_display_mode_shows_disabled()` in `tests/unit/cli/commands/test_admin_github_pr_setting.py` for complete examples.

**Mutation mode** (enable/disable): Assert via `admin.set_permission_calls` list which tracks all mutation calls as `(repo_root, enabled)` tuples.

See `test_enable_mode_sets_permission()` and `test_disable_mode_sets_permission()` in `tests/unit/cli/commands/test_admin_github_pr_setting.py` for complete examples.

**Key assertion pattern for mutations:**

```python
assert len(fake_admin.set_permission_calls) == 1
repo_root, enabled = fake_admin.set_permission_calls[0]
assert enabled is True
```

## erk_isolated_fs_env Helper

<!-- Source: tests/test_utils/env_helpers.py, erk_isolated_fs_env -->

Use `erk_isolated_fs_env()` to create an isolated environment with a configured git repo, GitHub remote, and proper Click context:

```python
from tests.test_utils.env_helpers import erk_isolated_fs_env

with erk_isolated_fs_env(runner) as env:
    ctx = env.build_context(github_admin=fake_admin, git=fake_git)
    result = runner.invoke(cli, ["admin", "github-pr-setting"], obj=ctx)
```

The `env.build_context()` method accepts gateway fakes as keyword arguments, injecting them into the Click context for the command under test.

## Standard Error Cases

1. **Missing GitHub remote**: Configure `FakeGit` with empty `remote_urls` to test `Ensure.not_none()` path. See `test_error_no_github_remote()` in both admin test files.

2. **Detached HEAD**: Omit `current_branch` from `build_context()` so `get_current_branch` returns `None`. See `test_error_detached_head()` in `test_admin_test_workflow.py`.

3. **Permission errors**: `FakeGitHubAdmin` can be extended to raise `RuntimeError` to test `UserFacingCliError` conversion.

## Reference Files

- `tests/unit/cli/commands/test_admin_github_pr_setting.py` — 5 test cases (display enabled/disabled, enable/disable mutation, no GitHub remote)
- `tests/unit/cli/commands/test_admin_test_workflow.py` — 4 test cases (happy path with/without issue, no GitHub remote, detached HEAD)
- `packages/erk-shared/src/erk_shared/gateway/github_admin/fake.py` — FakeGitHubAdmin implementation
