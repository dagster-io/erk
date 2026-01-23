# Plan: Display Missing Config Entries in `erk config list`

## Summary

Add display of missing configuration entries to `erk config list`:
- Global: `interactive_claude` section (model, verbose, permission_mode, dangerous, allow_dangerous)
- Repo: `pool.checkout.shell`, `pool.checkout.commands`, `plans.repo`

## File to Modify

`src/erk/cli/commands/config.py` - the `config_list` function (lines 236-327)

## Implementation

### 1. Add Interactive Claude Section to Global Config Display

After displaying the standard global config keys (line 271), add a new section for interactive Claude settings:

```python
# After the global config keys loop, add:
if ctx.global_config.interactive_claude:
    ic = ctx.global_config.interactive_claude
    user_output(click.style("\nInteractive Claude configuration:", bold=True))
    if ic.model:
        user_output(f"  interactive_claude.model={ic.model}")
    user_output(f"  interactive_claude.verbose={_format_config_value(ic.verbose)}")
    user_output(f"  interactive_claude.permission_mode={ic.permission_mode}")
    user_output(f"  interactive_claude.dangerous={_format_config_value(ic.dangerous)}")
    user_output(f"  interactive_claude.allow_dangerous={_format_config_value(ic.allow_dangerous)}")
```

### 2. Add Missing Repo Config Entries

After the existing `post_create.commands` display (around line 317), add:

```python
# pool.checkout.shell
if cfg.pool_checkout_shell:
    checkout_shell_source = " (local)" if local_only_config.pool_checkout_shell is not None else ""
    user_output(f"  pool.checkout.shell={cfg.pool_checkout_shell}{checkout_shell_source}")

# pool.checkout.commands
if cfg.pool_checkout_commands:
    has_local_checkout_commands = bool(local_only_config.pool_checkout_commands)
    checkout_cmds_source = " (includes local)" if has_local_checkout_commands else ""
    user_output(f"  pool.checkout.commands={cfg.pool_checkout_commands}{checkout_cmds_source}")

# plans.repo
if cfg.plans_repo:
    plans_repo_source = " (local)" if local_only_config.plans_repo is not None else ""
    user_output(f"  plans.repo={cfg.plans_repo}{plans_repo_source}")
```

### 3. Update "no custom config" Check

Update the `has_no_custom_config` check (lines 319-325) to include the new fields:

```python
has_no_custom_config = (
    not trunk_branch
    and cfg.pool_size is None
    and not cfg.env
    and not cfg.post_create_shell
    and not cfg.post_create_commands
    and not cfg.pool_checkout_shell
    and not cfg.pool_checkout_commands
    and not cfg.plans_repo
)
```

## Verification

1. Run `erk config list` and verify new sections appear
2. Test with interactive_claude config set in `~/.erk/config.toml`
3. Test with pool.checkout and plans.repo config set in `.erk/config.toml`