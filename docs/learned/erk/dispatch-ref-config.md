---
title: dispatch_ref Configuration
read_when:
  - "configuring which branch workflow_dispatch targets"
  - "working with .erk/config.toml dispatch settings"
  - "debugging workflow dispatch targeting the wrong branch"
tripwires:
  - action: "assuming dispatch_ref is project-level config"
    warning: "dispatch_ref is repo-level config (.erk/config.toml), overridable at local level (.erk/config.local.toml). It is not project-level."
---

# dispatch_ref Configuration

Override the default branch used for GitHub Actions `workflow_dispatch` events. By default, erk dispatches workflows against the repository's default branch (usually `master`). The `dispatch_ref` config allows targeting a different branch.

## Configuration

Top-level key in `.erk/config.toml`:

```toml
dispatch_ref = "my-custom-branch"
```

Can be overridden per-user in `.erk/config.local.toml`:

```toml
dispatch_ref = "my-dev-branch"
```

## Type Definition

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, LoadedConfig -->

`LoadedConfig` is a frozen dataclass with a `dispatch_ref: str | None` field. When `None`, the GitHub gateway calls `_get_default_branch()` via REST API to determine the repository's default branch. The result is cached per `repo_root` for the session.

## Config Loading

<!-- Source: src/erk/cli/config.py -->

Config loading reads `dispatch_ref` from TOML data, converting to `str` if present. Merge behavior: local config takes precedence over repo config when both are set.

## Call Sites

`dispatch_ref` is consumed at 4 locations, all passing it to `github.trigger_workflow(ref=ctx.local_config.dispatch_ref)`:

| Command              | Context                                             |
| -------------------- | --------------------------------------------------- |
| `erk pr dispatch`    | Dispatching plans for remote implementation         |
| `erk one-shot`       | Triggering one-shot workflows                       |
| `erk launch`         | Triggering pr-fix-conflicts, pr-address, pr-rewrite |
| `erk launch --learn` | Triggering learn workflows                          |

## Gateway Integration

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py -->

In `_dispatch_workflow_impl()`, if `ref` is provided it's used directly, bypassing the REST API call. When `None`, the gateway calls `_get_default_branch()` to fetch and cache the default branch.

## Related Documentation

- [Remote Workflow Template](remote-workflow-template.md) - How dispatched workflows execute
