---
title: Auto-Generated Reference Documentation
read_when:
  - "adding or modifying CLI commands"
  - "changing erk exec command structure"
  - "encountering outdated exec reference docs"
tripwires:
  - action: "adding or modifying CLI commands without regenerating reference docs"
    warning: "After CLI changes, run 'erk-dev gen-exec-reference-docs' to update auto-generated exec reference documentation. Stale docs confuse users and agents."
---

# Auto-Generated Reference Documentation

Erk maintains auto-generated reference documentation for `erk exec` commands. This documentation must be regenerated after any CLI structure changes.

## What Gets Auto-Generated

The command `erk-dev gen-exec-reference-docs` generates:

- Reference documentation for all `erk exec` subcommands
- Command syntax and option descriptions
- Help text from Click command definitions

## When to Regenerate

Run `erk-dev gen-exec-reference-docs` after:

- Adding a new `erk exec` command
- Modifying existing command options or arguments
- Changing command help text
- Renaming or removing commands
- Changing command structure (moving between groups)

## Why This Matters

The reference docs are used by:

- **Users**: Looking up command syntax
- **Agents**: Understanding available exec commands
- **CI**: Potentially validating command documentation

Stale documentation creates confusion when the actual CLI behavior doesn't match the docs.

## The Pattern

```bash
# After modifying CLI commands
erk-dev gen-exec-reference-docs

# Verify changes
git diff docs/

# Commit with your changes
git add docs/
git commit -m "Update exec reference docs"
```

## Integration with CI

While not currently enforced by CI, it's good practice to regenerate docs in the same commit as CLI changes. This keeps the documentation in sync with the code.

## Related Documentation

- [CLI Development](cli-development.md) - General CLI development patterns
- [erk exec Commands](erk-exec-commands.md) - Working with exec commands
