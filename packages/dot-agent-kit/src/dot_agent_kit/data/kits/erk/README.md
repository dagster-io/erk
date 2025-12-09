# Erk Kit for dot-agent

This directory contains the erk kit for dot-agent.

## IMPORTANT: Package Structure

**This is the correct location for erk kit commands:**
`packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk`

**Do NOT confuse with:**
`src/erk_dev/` (different package - erk development tools)

## Directory Structure

- `commands/` - Slash commands (`.md` files)
- `kit_cli_commands/` - Python CLI commands invoked by slash commands
- `agents/` - Agent definitions
- `docs/` - Documentation
- `kit.yaml` - Kit metadata

## Kit CLI Commands

Kit CLI commands are Python modules in `kit_cli_commands/` that:

1. Are invoked via `erk kit exec erk <command-name>`
2. Can return JSON (for programmatic use) or formatted text (for display)
3. Should handle errors internally and exit with proper status codes

### Best Practice: Display vs JSON Format

Commands should support both modes:

- `--format json` (default): Return structured JSON for programmatic use
- `--format display`: Return formatted text ready for user display

Example:

```python
if args.format == "display":
    print("✅ Operation successful")
    sys.exit(0)
else:
    return json.dumps({"success": True})
```
