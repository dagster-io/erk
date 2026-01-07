# Installation

Install erk and verify it's working correctly.

## Install erk

Install erk as a uv tool:

```bash
uv tool install erk
```

## Verify Installation

Run `erk doctor` to verify your installation:

```bash
cd your-project
erk doctor
```

Expected output shows checks for your environment:

```
Checking prerequisites...
✓ Python version: 3.11.5
✓ Claude Code installed
✓ uv installed
✓ GitHub CLI installed
ℹ Graphite (gt) not installed (optional)
ℹ Shell integration not configured (optional)

All required checks passed.
```

Note that Graphite and shell integration appear as info (ℹ) rather than errors. These are optional enhancements covered in later tutorials.

## Ready to Use

Once `erk doctor` passes the required checks, you're ready to use erk. When you run your first meaningful erk command (like `erk plan list`), erk will automatically initialize your repository:

- Creates `.erk/config.toml` with project settings
- Sets up Claude Code hooks for plan tracking
- Adds standard entries to `.gitignore`
- Syncs managed artifacts (skills, commands, workflows)

No manual `erk init` required for basic usage.

## See Also

- [Prerequisites](prerequisites.md) - Tools to install first
- [Shell Integration](shell-integration.md) - Enable directory switching (optional)
- [Your First Plan](first-plan.md) - Start using erk
