# Erk Kit

This directory contains the erk kit for Claude Code.

## IMPORTANT: Package Structure

**This is the correct location for erk kit commands:**
`packages/erk-kits/src/erk_kits/data/kits/erk`

**Do NOT confuse with:**
`src/erk/` (different package - erk CLI and core logic)

## Directory Structure

- `commands/` - Slash commands (`.md` files)
- `kit_cli_commands/` - Python CLI commands invoked by slash commands
- `agents/` - Agent definitions
- `docs/` - Documentation
- `kit.yaml` - Kit metadata

## Kit CLI Commands

Kit CLI commands are Python modules in `kit_cli_commands/` that:

1. Are invoked via `erk exec <command-name>`
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
