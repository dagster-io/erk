---
title: dispatch_ref Configuration
read_when:
  - "configuring which branch workflow_dispatch targets"
  - "working with .erk/config.toml dispatch settings"
  - "debugging workflow dispatch targeting the wrong branch"
  - "using --ref CLI option to override dispatch branch per run"
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

## CLI `--ref` Override

All three dispatch commands accept a `--ref` option for per-run branch override:

```bash
erk one-shot "fix the auth bug" --ref my-feature-branch
erk launch pr-address --pr 123 --ref my-feature-branch
erk pr dispatch 456 --ref my-feature-branch
```

**Priority chain:** `--ref` CLI flag > config `dispatch_ref` > repository default branch

<!-- Source: src/erk/cli/commands/launch_cmd.py, one_shot.py, pr/dispatch_cmd.py -->

Each command resolves the ref once before dispatching by checking the CLI flag first, falling back to config. This enables testing workflow changes on a feature branch without modifying config.

## Call Sites

`dispatch_ref` is consumed at 4 locations, all passing the resolved ref to `github.trigger_workflow(ref=ref)`:

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
