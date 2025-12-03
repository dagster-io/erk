---
title: CLI Development Documentation
read_when:
  - "building CLI commands"
  - "styling CLI output"
  - "organizing CLI command structure"
  - "implementing script mode"
---

# CLI Development Documentation

Guidance for building and styling CLI commands in erk.

## Quick Navigation

| When you need to...                       | Read this                                          |
| ----------------------------------------- | -------------------------------------------------- |
| Organize command structure                | [command-organization.md](command-organization.md) |
| Style output with colors and formatting   | [output-styling.md](output-styling.md)             |
| Format lists and tables                   | [list-formatting.md](list-formatting.md)           |
| Implement shell integration (script mode) | [script-mode.md](script-mode.md)                   |

## Documents in This Category

### Command Organization

**File:** [command-organization.md](command-organization.md)

Decision framework for CLI command structure: when to use top-level commands vs grouped subcommands, noun groupings, and the "plan is dominant noun" principle.

### Output Styling

**File:** [output-styling.md](output-styling.md)

Comprehensive guide to CLI output styling including colors, icons, headers, progress indicators, and semantic styling patterns.

### List Formatting

**File:** [list-formatting.md](list-formatting.md)

Patterns for formatting lists, tables, and structured data in CLI output.

### Script Mode

**File:** [script-mode.md](script-mode.md)

Implementing script mode for shell integration, allowing commands to output shell-evaluable strings for workflow automation.

## Related Topics

- [Architecture](../architecture/) - Patterns underlying CLI implementations
- [Commands](../commands/) - Slash command optimization patterns
