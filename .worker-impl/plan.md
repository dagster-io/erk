# Extraction Plan: SHELL_INTEGRATION_COMMANDS Registration Pattern

## Objective

Add documentation to prevent the silent failure bug pattern discovered when command groups are registered in SHELL_INTEGRATION_COMMANDS instead of specific subcommands.

## Source Information

- **Session analyzed**: 37e48d3c-0bcf-4590-8e5d-1e2962f70fde
- **Bug discovered**: `erk pr submit` silently exiting with no output
- **Root cause**: `"pr": pr_group` in SHELL_INTEGRATION_COMMANDS caused all pr subcommands to receive `--script` flag, but only `pr land` and `pr checkout` support it

## Documentation Item

### Type: Category A (Learning Gap)

**Location**: Update `docs/agent/architecture/shell-integration-patterns.md`

**Action**: Add new section

**Priority**: High - Prevents recurring silent failure bugs

### Draft Content

Add a new section "## Registering Commands for Shell Integration" after the existing content:

```markdown
## Registering Commands for Shell Integration

The `SHELL_INTEGRATION_COMMANDS` dictionary in `handler.py` determines which commands receive automatic `--script` injection when invoked through the shell wrapper.

### Critical Rule: Never Register Command Groups

**BAD**: Registering a group catches ALL subcommands:
```python
SHELL_INTEGRATION_COMMANDS = {
    "pr": pr_group,  # ❌ WRONG: ALL pr subcommands get --script injected
}
```

This causes silent failures because:
1. Handler calls `pr_group` with args `["submit", "--script"]`
2. Click routes to `pr_submit` which doesn't have `--script` option
3. Click fails with "No such option: --script" but error is swallowed
4. Result: exit code 1, no output to user

**GOOD**: Register specific subcommands that support `--script`:
```python
SHELL_INTEGRATION_COMMANDS = {
    "pr land": pr_land,        # ✅ Uses compound key
    "pr checkout": pr_checkout, # ✅ Uses compound key
    # pr_submit NOT registered - will passthrough correctly
}
```

### How Command Matching Works

The handler tries compound commands first:
1. For `erk pr land`, tries `"pr land"` → found → invokes `pr_land` with `--script`
2. For `erk pr submit`, tries `"pr submit"` → not found → tries `"pr"` → not found → passthrough

### Checklist for Adding Shell Integration

Before adding a command to `SHELL_INTEGRATION_COMMANDS`:

- [ ] Command has `--script` option defined
- [ ] Command outputs activation script path to stdout
- [ ] Use compound key for subcommands (e.g., `"wt create"` not `"wt"`)
- [ ] Never register a click.group() directly
```

## Validation

After implementing:
1. Verify the new section appears in shell-integration-patterns.md
2. Ensure it's linked from the architecture index
3. Verify it shows up in appropriate "read_when" conditions