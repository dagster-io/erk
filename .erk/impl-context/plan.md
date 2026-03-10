# Plan: `erk repo check` — Remote repo setup validation

## Context

When setting up erk's MCP server against a target GitHub repo, there's no way to verify that the repo has all required workflows, secrets, labels, and permissions configured — without a local checkout. This command inspects a remote repo via `gh api` and reports what's missing, with actionable remediation steps.

## Command Structure

- Human CLI: `erk repo check <owner/repo>`
- Machine CLI: `erk json repo check` (stdin JSON `{"repo": "owner/repo"}`)
- MCP tool: `repo_check` (auto-discovered via `@mcp_exposed`)

## What Gets Checked

| Category | Items | API |
|----------|-------|-----|
| Workflows | `plan-implement.yml`, `pr-rebase.yml`, `pr-address.yml`, `pr-rewrite.yml`, `one-shot.yml`, `learn.yml`, `consolidate-learn-plans.yml` | `GET /repos/{o}/{r}/contents/.github/workflows/{f}` |
| Secrets | `ERK_QUEUE_GH_PAT`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` | `GET /repos/{o}/{r}/actions/secrets/{name}` |
| Variable | `CLAUDE_ENABLED` (fail only if explicitly `"false"`) | `gh variable get --repo` |
| Permissions | `can_approve_pull_request_reviews` | `GET /repos/{o}/{r}/actions/permissions/workflow` |
| Labels | `erk-pr`, `erk-learn`, `erk-objective` | `GET /repos/{o}/{r}/labels/{name}` |

## New Files

```
src/erk/cli/commands/repo/
├── __init__.py              # repo_group Click group
└── check/
    ├── __init__.py          # empty
    ├── checks.py            # Individual check functions + RepoCheckItem
    ├── operation.py         # RepoCheckRequest, RepoCheckResult, run_repo_check()
    ├── cli.py               # Human command with [PASS]/[FAIL] output
    └── json_cli.py          # @mcp_exposed + @machine_command adapter

src/erk/cli/commands/json/repo/
├── __init__.py              # json_repo_group, registers json_repo_check
```

## Modified Files

- `src/erk/cli/cli.py` — import and register `repo_group`
- `src/erk/cli/commands/json/__init__.py` — import and register `json_repo_group`

## Implementation Details

### `checks.py` — Individual check functions

```python
@dataclass(frozen=True)
class RepoCheckItem:
    name: str
    passed: bool
    message: str
    remediation: str | None
```

Each check function takes `owner: str, repo: str` and returns `RepoCheckItem`. All use `subprocess.run` with `gh api` directly — no gateway layer needed since this is remote-only and doesn't need a local `Path` for `cwd`.

Key functions:
- `check_workflow_exists(owner, repo, filename)` — 200 = exists, 404 = missing
- `check_secret_exists(owner, repo, secret_name)` — pattern from `RealGitHubAdmin.secret_exists()`
- `check_variable_not_disabled(owner, repo, variable_name)` — passes if unset or any value except `"false"`
- `check_workflow_permissions(owner, repo)` — pattern from `RealGitHubAdmin.get_workflow_permissions()`
- `check_label_exists(owner, repo, label_name)` — 200 = exists, 404 = missing

Use workflow names from `src/erk/cli/constants.py` (`WORKFLOW_COMMAND_MAP` values) rather than hardcoding.

Use label definitions from `erk_shared.gateway.github.objective_issues.get_required_erk_labels()` for label names/colors/descriptions (used by remediation strings).

### `operation.py`

```python
@dataclass(frozen=True)
class RepoCheckRequest:
    repo: str  # "owner/repo" format

@dataclass(frozen=True)
class RepoCheckResult:
    repo: str
    checks: tuple[RepoCheckItem, ...]
    # to_json_dict() serializes checks array + all_passed bool
```

`run_repo_check(request)` validates format, splits owner/repo, runs all checks, returns result. Does NOT need `ErkContext` — pure subprocess calls.

### `json_cli.py` — follows `src/erk/cli/commands/pr/view/json_cli.py` pattern

Decorator stack: `@mcp_exposed` > `@machine_command` > `@click.command` > `@click.pass_obj`

### `cli.py` — follows `src/erk/cli/commands/objective/check/cli.py` pattern

Takes `REPO` as a Click argument. Renders `[PASS]`/`[FAIL]` per check with color. Summary line at bottom. Exit code 1 if any check failed.

## Key Patterns to Reuse

- `WORKFLOW_COMMAND_MAP` values from `src/erk/cli/constants.py` for workflow filenames
- `get_required_erk_labels()` from `erk_shared.gateway.github.objective_issues` for label definitions
- `MachineCommandError` from `erk_shared.agentclick.machine_command` for error returns
- Subprocess patterns from `packages/erk-shared/src/erk_shared/gateway/github_admin/real.py` (secret_exists, get_workflow_permissions)

## Verification

1. `erk repo check schrockn/erk` — should show all checks passing on the erk repo itself
2. `echo '{"repo": "schrockn/erk"}' | erk json repo check` — JSON output with `all_passed: true`
3. `erk repo check schrockn/some-unconfigured-repo` — should show failures with remediation
4. Unit tests for operation.py mocking subprocess.run
5. Run `make fast-ci` to verify lint/format/type checks pass
