# Launch Claude in dangerous mode for `erk codespace run objective plan -d`

## Context

When running `erk codespace run objective plan -d 9318`, the `-d` flag propagates to `erk objective plan -d`, which currently only sets `allow_dangerous_override=True`. This passes `--allow-dangerously-skip-permissions` to Claude, which merely *allows* the user to opt into skipping prompts during the session. The user wants actual dangerous mode (`--dangerously-skip-permissions`), which skips all permission prompts automatically.

## Change

**File:** `src/erk/cli/commands/objective/plan_cmd.py` (line ~738)

Change:
```python
    config = ia_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,  # <-- always None, never activates dangerous mode
        allow_dangerous_override=allow_dangerous_override,
    )
```

To:
```python
    config = ia_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=True if dangerous else None,
        allow_dangerous_override=allow_dangerous_override,
    )
```

This makes `-d` set both `dangerous=True` and `allow_dangerous=True` on the config, which causes `build_claude_args()` in `erk_shared/gateway/agent_launcher/real.py` to emit both `--dangerously-skip-permissions` and `--allow-dangerously-skip-permissions`.

## Verification

- Run `erk objective plan -d <issue>` and confirm Claude launches with `--dangerously-skip-permissions` in its args
- Existing tests for `build_claude_args` and `InteractiveAgentConfig.with_overrides` cover the flag propagation
