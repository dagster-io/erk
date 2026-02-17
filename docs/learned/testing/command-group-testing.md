---
title: Command Group Testing
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - "testing Click command groups with invoke_without_command=True"
  - "writing tests for commands that serve as both group and default action"
tripwires:
  - action: "testing only the subcommand path of a group with invoke_without_command=True"
    warning: "Groups with default behavior need tests for BOTH paths: direct invocation (no subcommand) and explicit subcommand invocation. Missing either path is a coverage gap."
  - action: "passing group-level options when invoking a subcommand in tests"
    warning: "Click does NOT propagate group-level options to subcommands by default. Options placed before the subcommand name in the args list are silently ignored."
---

# Command Group Testing

Testing patterns for Click command groups that use `invoke_without_command=True`, where the group itself executes behavior when no subcommand is given.

## Why This Needs Special Attention

`invoke_without_command=True` creates a dual-path command: the group runs its own logic when invoked directly, but delegates to a subcommand when one is specified. This means a single command registration creates **two distinct execution paths** that must be tested independently. Agents naturally test the more common path and forget the other.

## Historical Context

Erk originally used `invoke_without_command=True` to unify local/remote command variants (e.g., `erk pr address` for local, `erk pr address remote` for remote). This pattern was abandoned because local and remote execution have fundamentally different preconditions, options, and error modes. See [Local/Remote Command Group Pattern (Deprecated)](../cli/local-remote-command-groups.md) for the full rationale.

<!-- Source: src/erk/cli/commands/init/__init__.py, init_group() -->

The only remaining use is `erk init`, where it works because the default action (full initialization) and subcommands (`erk init capability add/remove/list`) share the same domain and preconditions. See `init_group()` in `src/erk/cli/commands/init/__init__.py` for the implementation, and `tests/unit/cli/commands/init/capability/` for test examples.

## Two-Path Test Coverage

Every group with `invoke_without_command=True` requires tests for both invocation paths:

| Path           | Invocation shape               | What to verify                                                           |
| -------------- | ------------------------------ | ------------------------------------------------------------------------ |
| **Default**    | `["group-name", "--flag"]`     | Group function runs when `ctx.invoked_subcommand is None`                |
| **Subcommand** | `["group-name", "sub", "arg"]` | Subcommand takes over, group function is skipped or acts as pass-through |

Missing either path is a silent coverage gap — Click handles the routing, so the untested path won't fail loudly until production.

## Click Option Propagation Gotcha

Group-level options (`@click.option` on the group function) do **not** propagate to subcommands by default. This is a Click design choice that causes subtle test failures:

```python
# WRONG: --force is defined on the group, not the subcommand
# Click silently ignores it when a subcommand is specified
runner.invoke(cli, ["init", "--force", "capability", "add", "foo"], obj=ctx)
```

When this matters: if a group has options that should affect subcommand behavior, the group function must store them in `ctx.ensure_object(dict)` or pass them via `ctx.obj`, and the subcommand must read them from context. This is additional wiring that needs its own test coverage.

## Context Dependencies Differ by Path

Different invocation paths often need different fake dependencies. The group's default path and its subcommands may use entirely different gateways:

| If path uses...         | Provide in `ErkContext.for_test()`                          |
| ----------------------- | ----------------------------------------------------------- |
| External tool execution | `prompt_executor=FakePromptExecutor()`                      |
| GitHub API access       | `github=FakeGitHub()` or `github_issues=FakeGitHubIssues()` |
| Git operations          | `git=FakeGit(...)`                                          |
| Filesystem state        | `cwd=tmp_path` with pre-created directory structure         |

Providing the wrong fake for a path produces confusing errors. Check what gateway each path actually calls before writing the test.

## Related Documentation

- [Local/Remote Command Groups (Deprecated)](../cli/local-remote-command-groups.md) — Why the unified local/remote pattern was abandoned, and the decision framework for when `invoke_without_command=True` is appropriate
- [CLI Testing Patterns](cli-testing.md) — General `ErkContext.for_test()` patterns for CLI tests
- [Exec Script Testing](exec-script-testing.md) — Testing patterns for exec scripts
