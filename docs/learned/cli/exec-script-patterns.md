---
title: Exec Script Patterns
category: cli
read_when:
  - "Creating new exec CLI commands"
  - "Understanding why exec commands use context injection instead of Path.cwd()"
  - "Deciding where to import gateway ABCs from"
tripwires:
  - action: "importing from erk_shared.gateway.{service}.abc when creating exec commands"
    warning: "Gateway ABCs use submodule paths: `erk_shared.gateway.{service}.{resource}.abc`"
  - action: "using Path.cwd() or Path.home() in exec scripts"
    warning: "Use context injection via require_cwd(ctx) for testability"
last_audited: "2026-02-08"
audit_result: edited
---

# Exec Script Patterns

Exec scripts are Click commands in `src/erk/cli/commands/exec/scripts/` that execute specific operations (update GitHub issues, manipulate git state, compute derived data). They differ from top-level erk commands in two ways: (1) they use mandatory context injection for all dependencies, and (2) they always output JSON for programmatic consumption.

## Why Context Injection Is Mandatory

The core design decision: **exec scripts never call `Path.cwd()`, `Path.home()`, or construct gateways directly**. All dependencies come through Click's context object via `require_*` helpers.

### The Testability Problem

Without context injection, testing requires filesystem manipulation:

```python
# WRONG: Impossible to test without changing directories
def my_command() -> None:
    progress_file = Path.cwd() / ".impl" / "progress.md"
    if progress_file.exists():
        # ... process file
```

This forces tests to use `monkeypatch.chdir()` or actually create `.impl/` directories in test fixtures. When multiple tests run in parallel, directory changes create race conditions.

With context injection, tests inject a controlled `cwd` value:

```python
# CORRECT: Test injects cwd without filesystem manipulation
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)
    progress_file = cwd / ".impl" / "progress.md"
    if progress_file.exists():
        # ... process file

# Test passes tmp_path as cwd
result = runner.invoke(my_command, obj=ErkContext.for_test(cwd=tmp_path))
```

The test controls where the command looks for files without changing the process's working directory. This enables hermetic, parallelizable tests.

### Explicit Dependency Graph

Context injection makes dependencies visible in the function signature:

<!-- Source: src/erk/cli/commands/exec/scripts/list_sessions.py, imports -->
<!-- Source: packages/erk-shared/src/erk_shared/context/helpers.py, require_* functions -->

See `require_cwd()`, `require_git()`, `require_github()` in `packages/erk-shared/src/erk_shared/context/helpers.py`. Each helper:

1. Checks that context is initialized (LBYL)
2. Returns the typed dependency
3. Exits with clear error if missing

This eliminates "where did this dependency come from?" questions during code review.

## Template Location

For the full exec script template (result dataclasses, Click entry point structure, context helpers table), see:

<!-- Source: src/erk/cli/commands/exec/scripts/AGENTS.md -->

`src/erk/cli/commands/exec/scripts/AGENTS.md` — auto-loaded when editing exec scripts, contains required pattern and anti-patterns.

## Gateway Import Path Convention

Gateway ABCs live in **submodule paths**, not top-level `erk_shared.gateway.{service}.abc`:

```python
# CORRECT: submodule path
from erk_shared.gateway.github.issues.abc import GitHubIssues

# WRONG: will raise ImportError
from erk_shared.gateway.github.abc import GitHubIssues
```

### Why Not Top-Level?

The gateway package is decomposed into resource-specific modules (issues, pull requests, workflows). Each resource has its own ABC interface. Top-level `github.abc` doesn't exist because there's no single "GitHub" interface — there are multiple orthogonal resources.

This forces import sites to be explicit about which resource they're using, making dependencies clearer.

## Plan Metadata Helpers

Plan header operations (extracting plan content from issues, finding metadata comment IDs) live in a dedicated module, not in the generic GitHub gateway:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py -->

See `erk_shared.gateway.github.metadata.plan_header` for `extract_plan_header_comment_id()` and `extract_plan_from_comment()`. These are kept separate from the GitHub Issues gateway because they operate on plan-specific metadata block formats, not generic issue operations.

## Error Code Convention

Use lowercase `snake_case` error codes that are:

1. **Machine-readable** — callers can parse and branch on the code
2. **Descriptive** — `missing_erk_plan_label` not `invalid_input`
3. **Actionable** — users understand what went wrong from the code alone

Example from real exec scripts:

```json
{
  "success": false,
  "error": "missing_erk_plan_label",
  "message": "Issue #123 does not have the 'erk-plan' label"
}
```

The error code doubles as documentation of the failure mode.

## URL Construction With Repo Identity

Never hardcode repository names when constructing GitHub URLs. Use `get_repo_identifier(ctx)` from `erk_shared.context.helpers`:

<!-- Source: packages/erk-shared/src/erk_shared/context/helpers.py, get_repo_identifier -->

```python
repo_id = get_repo_identifier(ctx)
if repo_id is None:
    # handle non-GitHub repo
    return ErrorResult(...)

url = f"https://github.com/{repo_id}/issues/{issue_number}"
```

The helper returns `"owner/repo"` format or `None` if not in a GitHub-connected repository. Always check for `None` before constructing URLs (LBYL pattern).

### Why Not Pass Repo As Parameter?

We could make every exec command take `--owner` and `--repo` flags. But 99% of calls happen from the current repository, and forcing flags creates noise. The context provides the repo identity automatically when available.

For the 1% of cross-repo operations (e.g., plans stored in a separate repo), exec scripts take explicit `--repo` flags that override the context.

## Result Dataclass Pattern

Exec commands return frozen dataclasses with discriminated union error handling:

```python
@dataclass(frozen=True)
class SuccessResult:
    success: bool  # Always True
    # ... success-specific fields

@dataclass(frozen=True)
class ErrorResult:
    success: bool  # Always False
    error: str     # Machine-readable code
    message: str   # Human-readable explanation
```

The `success` field discriminates the union. Callers check `success` first, then access type-specific fields. This makes error handling explicit without exceptions.

See the co-located `AGENTS.md` for the full template.

## See Also

- [CLI Dependency Injection Patterns](../cli/dependency-injection-patterns.md) — deep dive on why context injection exists
- [Exec Script Testing Patterns](../testing/exec-script-testing.md) — how to write tests for exec commands
- [fake-driven-testing skill](/.claude/skills/fake-driven-testing/) — 5-layer test architecture
