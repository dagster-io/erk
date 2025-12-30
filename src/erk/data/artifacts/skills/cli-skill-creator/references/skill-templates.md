# CLI Skill Templates

This reference provides reusable templates for structuring CLI skills. Use these as starting points and adapt based on the specific CLI tool being documented.

## Core Template: CLI Skill Structure

```markdown
---
name: <cli-tool-name>
description: This skill should be used when working with <tool-name> for <primary-purpose>. Use when users mention <tool-name> commands, <key-workflows>, or <main-use-cases>. Essential for understanding <tool-name>'s mental model, command structure, and <key-integrations>.
---

# <CLI Tool Name>

## Overview

<Tool-name> is a <tool-category> that <what-it-does>. This skill provides comprehensive guidance for using <tool-name> to <key-benefits>, including <main-features>.

## When to Use This Skill

Invoke this skill when users:

- Mention <tool-name> commands or workflows
- Ask about <primary-use-case>
- Need help with <key-feature-1>
- Want to understand <tool-name>'s mental model or command structure
- Request guidance on <key-feature-2>
- Ask about <integration-point>
- Need help with <tool-name> configuration or setup
- Request integration patterns between <tool-name> and <related-tools>

## Core Concepts

Before providing guidance, understand these key concepts:

**<Concept-Category-1>:**

- <Key concept 1> - <Brief explanation>
- <Key concept 2> - <Brief explanation>
- <Key concept 3> - <Brief explanation>

**<Concept-Category-2>:**

<Explanation of second major concept category>

**Mental Model:**

<One paragraph explaining how users should think about this tool>

## Using the Reference Documentation

When providing <tool-name> guidance, load the comprehensive reference documentation:
```

references/<tool-name>\_reference.md

```

This reference contains:

- Complete mental model and terminology
- Full command reference for <primary-commands>
- Configuration patterns
- Workflow patterns for common scenarios
- Integration details (<related-tools>)
- Practical examples for daily development

**Loading Strategy:**

- Always load `references/<tool-name>_reference.md` when user asks <tool-name>-related questions
- Use grep patterns to find specific sections when needed:
  - `<command-1>` - <Description>
  - `<command-2>` - <Description>
  - `Pattern [0-9]:` - Workflow patterns
  - `Configuration` - Setup
  - `<Integration>` - Integration with <other-tool>

## Common Operations

When users ask for help with <tool-name>, guide them using these patterns:

### First-Time Setup

1. Check if <tool-name> is installed: `<tool-name> --version`
2. Initialize/authenticate: `<tool-name> <init-command>`
3. Configure defaults: `<tool-name> config <key> <value>`
4. Test connection: `<tool-name> <test-command>`

### <Primary-Feature-1>

Load `references/<tool-name>_reference.md` and search for "<feature-1>" section to provide:

- <Operation-1>: `<command-1>`
- <Operation-2>: `<command-2>`
- <Operation-3>: `<command-3>`

### <Primary-Feature-2>

Load `references/<tool-name>_reference.md` and search for "<feature-2>" section to provide:

- <Operation-1>: `<command-1>`
- <Operation-2>: `<command-2>`

## Workflow Guidance

When users describe their workflow needs, map them to patterns in the reference:

**Pattern 1: <Workflow-Name>** - <Brief description>
**Pattern 2: <Workflow-Name>** - <Brief description>
**Pattern 3: <Workflow-Name>** - <Brief description>

Load the appropriate pattern sections from `references/<tool-name>_reference.md` based on user needs.

## <Integration-Category>

When users need <integration-specific> help:

1. Load the <Integration> section from `references/<tool-name>_reference.md`
2. Explain <integration-concept-1>
3. Show <integration-pattern>
4. Guide on <integration-best-practice>

## Troubleshooting

When users encounter issues:

1. Check <diagnostic-1>: `<tool-name> <check-command-1>`
2. Verify <diagnostic-2>: `<tool-name> <check-command-2>`
3. Review <diagnostic-3>: `<tool-name> <check-command-3>`
4. Enable debug mode: `<DEBUG_VAR>=1 <tool-name> <command>`

Load the Troubleshooting section from `references/<tool-name>_reference.md` for specific error patterns.

## Resources

### references/

- `<tool-name>_reference.md` - Comprehensive <tool-name> mental model and command reference

This reference should be loaded whenever providing <tool-name> guidance to ensure accurate, detailed information.
```

## Command Reference Template

Use this template for the main reference documentation file:

````markdown
# <CLI Tool Name> - Complete Reference

## Mental Model

### Overview

<Tool-name> is built around <core-concept>. Understanding this mental model is essential for effective use.

### Core Concepts

**<Concept-1>**

<Detailed explanation of first core concept>

**<Concept-2>**

<Detailed explanation of second core concept>

### Terminology

| Term     | Definition   |
| -------- | ------------ |
| <Term-1> | <Definition> |
| <Term-2> | <Definition> |
| <Term-3> | <Definition> |

### Architecture

<Explanation of how the tool is structured>

## Command Reference

### Global Options

Options that work with all commands:

| Flag        | Description    | Example                  |
| ----------- | -------------- | ------------------------ |
| `--help`    | Display help   | `<tool> --help`          |
| `--version` | Show version   | `<tool> --version`       |
| `--verbose` | Verbose output | `<tool> --verbose <cmd>` |

### <Command-Category-1>

#### `<command-1>`

**Purpose:** <What this command does>

**Syntax:**

```bash
<tool> <command-1> [OPTIONS] <ARGS>
```
````

**Options:**

| Flag         | Description   | Default   |
| ------------ | ------------- | --------- |
| `-f, --flag` | <Description> | <Default> |

**Examples:**

```bash
# <Example description>
<tool> <command-1> <args>

# <Another example>
<tool> <command-1> --flag <value>
```

**Related Commands:** `<related-cmd-1>`, `<related-cmd-2>`

### <Command-Category-2>

<Repeat pattern for other command categories>

## Workflow Patterns

### Pattern 1: <Workflow-Name>

**Use case:** <When to use this pattern>

**Steps:**

1. <Step-1>
   ```bash
   <command-1>
   ```

2. <Step-2>
   ```bash
   <command-2>
   ```

3. <Step-3>
   ```bash
   <command-3>
   ```

**Example:**

```bash
# <Scenario description>
<complete-workflow-example>
```

### Pattern 2: <Workflow-Name>

<Repeat for other workflows>

## Configuration

### Configuration File Locations

- Global: `~/.config/<tool>/config`
- Project: `./<tool-config-file>`
- Environment: `<TOOL_VAR>` environment variables

### Configuration Options

| Setting   | Description   | Default     | Example     |
| --------- | ------------- | ----------- | ----------- |
| `<key-1>` | <Description> | `<default>` | `<example>` |

### Configuration Examples

```toml
# Global configuration (~/.config/<tool>/config)
<setting-1> = "<value>"
<setting-2> = true
```

## Integration

### <Integration-1>

**How <tool> integrates with <other-tool>:**

<Explanation of integration>

**Common patterns:**

```bash
# <Pattern description>
<tool> <command> | <other-tool> <command>
```

### <Integration-2>

<Repeat for other integrations>

## Troubleshooting

### Common Issues

#### <Issue-1>

**Symptoms:** <What user sees>

**Cause:** <Why it happens>

**Solution:**

```bash
<fix-command>
```

#### <Issue-2>

<Repeat for other issues>

### Debugging

**Enable debug output:**

```bash
<DEBUG_VAR>=1 <tool> <command>
```

**Check logs:**

```bash
<tool> logs
# or
cat ~/.config/<tool>/logs/<log-file>
```

## Advanced Usage

### <Advanced-Topic-1>

<Deep dive into advanced feature>

### <Advanced-Topic-2>

<Deep dive into another advanced feature>

## Best Practices

1. **<Practice-1>** - <Explanation>
2. **<Practice-2>** - <Explanation>
3. **<Practice-3>** - <Explanation>

## Common Gotchas

- **<Gotcha-1>** - <Why it trips people up and how to avoid>
- **<Gotcha-2>** - <Why it trips people up and how to avoid>

## Resources

- Official documentation: <URL>
- GitHub repository: <URL>
- Community forum: <URL>

````

## Workflow Pattern Template

Use this template for documenting individual workflow patterns:

```markdown
### Pattern N: <Workflow-Name>

**Use case:** <Describe when this pattern applies>

**Prerequisites:**
- <Prerequisite-1>
- <Prerequisite-2>

**Steps:**

1. **<Step-name>**

   <Explanation of what this step does>

   ```bash
   <command>
````

Expected output:

```
<sample-output>
```

2. **<Step-name>**

   <Explanation>

   ```bash
   <command>
   ```

3. **<Step-name>**

   <Explanation>

   ```bash
   <command>
   ```

**Complete Example:**

```bash
# <Scenario description>

# Step 1
<command-1>

# Step 2
<command-2>

# Step 3
<command-3>

# Result: <What was accomplished>
```

**Variations:**

- **<Variation-1>:** <When to use> - `<alternative-command>`
- **<Variation-2>:** <When to use> - `<alternative-command>`

**Related Patterns:** Pattern <N>, Pattern <M>

````

## Integration Section Template

Use this template for documenting integrations with other tools:

```markdown
## <Tool-Name> Integration

### Overview

<High-level explanation of how <main-tool> works with <other-tool>>

### Prerequisites

- <Other-tool> installed and configured
- <Any-other-requirements>

### Integration Points

**<Integration-point-1>**

<Explanation>

Example:
```bash
<integrated-command-example>
````

**<Integration-point-2>**

<Explanation>

### Common Workflows

#### Workflow: <Integrated-workflow-name>

```bash
# <Step-1>
<tool-1> <command>

# <Step-2>
<tool-2> <command>

# <Step-3>
<tool-1> <command> | <tool-2> <command>
```

### Configuration

<Tool-specific> configuration for <other-tool> integration:

```<config-format>
<integration-config-example>
```

### Troubleshooting Integration

**Issue:** <Common integration problem>

**Solution:** <How to fix>

```bash
<fix-command>
```

````

## Troubleshooting Section Template

Use this template for troubleshooting documentation:

```markdown
## Troubleshooting

### Diagnostic Commands

Run these commands to gather diagnostic information:

```bash
# Check version
<tool> --version

# Check configuration
<tool> config list

# Check connectivity/status
<tool> status

# Enable debug mode
<DEBUG_VAR>=1 <tool> <command>

# Check logs
<tool> logs
# or
cat ~/.config/<tool>/log
````

### Common Error Messages

#### Error: <error-message>

**What it means:** <Explanation>

**Common causes:**

- <Cause-1>
- <Cause-2>

**How to fix:**

1. <Fix-step-1>
   ```bash
   <fix-command-1>
   ```

2. <Fix-step-2>
   ```bash
   <fix-command-2>
   ```

**Prevention:** <How to avoid this error>

#### Error: <another-error-message>

<Repeat pattern>

### Common Problems

#### Problem: <problem-description>

**Symptoms:**

- <Symptom-1>
- <Symptom-2>

**Diagnosis:**

```bash
# Check <diagnostic>
<diagnostic-command>
```

**Solution:**

```bash
# <Fix description>
<fix-commands>
```

### Getting Help

If troubleshooting steps don't resolve the issue:

1. Check GitHub issues: `<github-url>/issues`
2. Enable debug mode and capture output
3. Provide minimal reproduction case
4. Include version: `<tool> --version`
5. Community forum: <forum-url>

````

## Quick Reference Template

For creating a concise quick reference card:

```markdown
# <Tool-Name> Quick Reference

## Essential Commands

| Task | Command |
|------|---------|
| <Task-1> | `<tool> <cmd-1>` |
| <Task-2> | `<tool> <cmd-2>` |
| <Task-3> | `<tool> <cmd-3>` |

## Common Flags

| Flag | Purpose |
|------|---------|
| `--help` | Show help |
| `--version` | Show version |
| `--verbose` | Verbose output |
| `--dry-run` | Preview without executing |

## Quick Workflows

### <Workflow-1>
```bash
<tool> <cmd-1>
<tool> <cmd-2>
<tool> <cmd-3>
````

### <Workflow-2>

```bash
<tool> <cmd-1>
<tool> <cmd-2>
```

## Configuration

```<format>
# Location: ~/.config/<tool>/config
<key-1> = "<value>"
<key-2> = true
```

## Troubleshooting

| Problem     | Solution      |
| ----------- | ------------- |
| <Problem-1> | `<fix-cmd-1>` |
| <Problem-2> | `<fix-cmd-2>` |

## Resources

- Docs: <url>
- GitHub: <url>

```

## Adaptation Guidelines

### When to Use Each Template

1. **Core Template** - Always use for main skill.md file
2. **Command Reference Template** - For comprehensive reference documentation in references/
3. **Workflow Pattern Template** - When documenting specific multi-step processes
4. **Integration Section Template** - When documenting how CLI works with other tools
5. **Troubleshooting Section Template** - For dedicated troubleshooting docs
6. **Quick Reference Template** - For concise cheat-sheet style reference

### Customization Tips

**For simple CLI tools (< 10 commands):**
- Combine command reference and workflow patterns in single file
- May not need separate references/ directory
- Focus on examples over exhaustive documentation

**For complex CLI tools (> 20 commands, multiple subcommands):**
- Use full template structure with separate reference files
- Organize commands by category/domain
- Create multiple reference files by topic
- Include extensive workflow patterns

**For API-wrapper CLIs:**
- Emphasize JSON output patterns
- Document authentication thoroughly
- Map CLI commands to API operations
- Include rate limiting guidance

**For infrastructure/DevOps CLIs:**
- Focus on CI/CD integration patterns
- Document non-interactive modes
- Emphasize safety (dry-run, confirmation)
- Include rollback procedures

### Template Variables Reference

Replace these placeholders when using templates:

- `<cli-tool-name>` - Hyphenated tool name (e.g., `my-cli`)
- `<CLI Tool Name>` - Display name (e.g., `My CLI`)
- `<tool-name>` - Lowercase tool name (e.g., `mycli`)
- `<tool>` - Command name as typed (e.g., `mycli`)
- `<primary-purpose>` - Main use case (e.g., `container management`)
- `<key-workflows>` - Primary workflows (e.g., `deployment, scaling`)
- `<main-use-cases>` - Common tasks (e.g., `CI/CD automation`)
- `<key-integrations>` - Integration points (e.g., `GitHub, AWS`)
- `<command>` - Specific command name
- `<args>` - Command arguments
- `<flags>` - Command flags/options

## Examples from Existing Skills

### gh Skill Structure

The gh skill demonstrates:
- Clear "When to Use" section with specific triggers
- Core Concepts explaining three-layer architecture
- Progressive loading strategy for large reference docs
- Workflow patterns numbered for easy reference
- Integration sections for erk and git
- GraphQL as specialized subdomain with own reference

### graphite Skill Structure

The graphite skill demonstrates:
- Core Mental Model section explaining stacks
- Visual diagrams using ASCII art
- Essential Commands table for quick lookup
- Workflow Patterns with numbered steps
- Common Mistakes section (anti-patterns)
- Integration section for erk
- Quick Decision Tree for when to use what

### erk Skill Structure

The erk skill demonstrates:
- Core Concepts distinguishing related terms
- Directory structure visualization
- Loading Strategy for reference docs
- Common Operations organized by lifecycle
- Configuration Guidance with hierarchy
- Architecture section for contributors

## Key Principles

When adapting these templates:

1. **Progressive Disclosure** - Simple concepts first, complexity later
2. **Example-Driven** - Show real commands and output
3. **Mental Model Focus** - Help users think correctly about the tool
4. **Practical Organization** - Organize by task/workflow, not alphabetically
5. **Cross-Reference** - Link related concepts and commands
6. **Maintainability** - Structure for easy updates as tool evolves

---

These templates provide starting points. The best CLI skills adapt these patterns to match the specific tool's design philosophy and user mental models.
```
