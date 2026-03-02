# Plan: Improve "Using existing branch" message for `--for-plan` flows

## Context

When running `erk br co --for-plan <number>`, the message "Using existing branch: {branch}" is ambiguous — it could sound like a fallback or warning. Since the branch was deliberately created by `plan-save`, the message should convey that we're intentionally checking it out.

## Changes

Two files, one-line change each:

### 1. `src/erk/cli/commands/branch/checkout_cmd.py` (line 519)

```python
# Before:
user_output(f"Using existing branch: {branch}")

# After:
user_output(f"Checking out plan branch: {branch}")
```

### 2. `src/erk/cli/commands/branch/create_cmd.py` (line 170)

```python
# Before:
user_output(f"Using existing branch: {branch_name}")

# After:
user_output(f"Checking out plan branch: {branch_name}")
```

Both messages are gated behind `if setup is not None` (i.e., `--for-plan` was used), so this only affects plan workflows where the branch existing is expected behavior.

## Verification

- Run `erk br co --for-plan <plan-number>` for a plan whose branch already exists locally — confirm new message
- Run `erk br create --for-plan <plan-number>` same scenario — confirm new message
