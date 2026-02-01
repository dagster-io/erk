---
title: Command Documentation as Executable Specification
read_when:
  - "creating or editing slash commands"
  - "modifying files in .claude/commands/"
  - "seeing CI failures related to Prettier"
  - "writing command documentation"
  - "updating command prompts or instructions"
tripwires:
  - action: "editing .claude/commands/ files"
    warning: "Run `make prettier` immediately after editing command files. Formatting affects CI validation and is non-obvious. CI will fail without it."
---

# Command Documentation as Executable Specification

## Overview

Files in `.claude/commands/` are **executable specifications**, not just documentation. When you edit a command file, the changes take effect immediately. The formatting, structure, and content are all part of the executable behavior.

## Core Principle

**Command files are code, not comments.**

Changes to `.claude/commands/*.md` files are executed by Claude Code when users invoke the command. Treat these files with the same rigor as Python source code.

## Immediate Effect

When you edit a command file:

1. **No compilation needed** - Changes are live immediately
2. **Format matters** - Markdown structure affects parsing
3. **Content is instructions** - Claude Code executes what you write
4. **CI validates format** - Prettier is enforced

## Prettier Requirement

**After editing any `.claude/commands/*.md` file, run `make prettier` immediately.**

### Why Prettier is Required

- **CI enforcement** - Prettier checks are mandatory in CI
- **Consistency** - Ensures uniform formatting across commands
- **Parsing reliability** - Consistent format → reliable execution
- **Review clarity** - Formatted diffs are easier to review

### Workflow

```bash
# Edit command file
vim .claude/commands/erk/my-command.md

# Format immediately
make prettier

# Verify changes
git diff .claude/commands/erk/my-command.md

# Commit
git add .claude/commands/erk/my-command.md
git commit -m "Update my-command instructions"
```

## Command File Structure

### Required Sections

```markdown
# /command-name

Brief description of what the command does.

## Prerequisites

- Required tools or environment setup
- Access requirements (GitHub auth, etc.)

## Usage

\`\`\`bash
/command-name [arguments]
\`\`\`

## Agent Instructions

### Step 1: {Action}

Detailed instructions for the agent to execute.

### Step 2: {Action}

More instructions...

## Related Commands

- Other relevant commands
```

### Content Guidelines

- **Be explicit** - Agent executes exactly what you write
- **Use code blocks** - For commands agent should run
- **Include error handling** - What to do when things fail
- **Define output format** - How agent should report results
- **Link related docs** - Reference learned docs when relevant

## Common Mistakes

❌ **Editing without Prettier** - CI will fail
❌ **Vague instructions** - Agent won't know what to do
❌ **Missing error handling** - Agent fails silently
❌ **No output format** - Inconsistent user experience
✅ **Run Prettier immediately** - After every edit
✅ **Explicit, ordered steps** - Agent can follow reliably
✅ **Error paths defined** - What to do when step fails
✅ **Output format specified** - Consistent reporting

## Testing Command Changes

### Local Testing

```bash
# Edit command
vim .claude/commands/erk/my-command.md

# Format
make prettier

# Test in Claude Code
/erk:my-command [test-args]

# Verify behavior matches intent
```

### CI Validation

CI checks:

- Prettier formatting (via `make prettier-check`)
- Markdown syntax validity
- Frontmatter structure (if used)

If CI fails on Prettier:

1. Run `make prettier` locally
2. Commit formatted changes
3. Push again

## Versioning and Changes

### Breaking Changes

If command behavior changes significantly:

1. **Update command docs** - Reflect new behavior
2. **Test thoroughly** - Ensure old use cases still work or fail gracefully
3. **Update related docs** - If command is referenced elsewhere
4. **No deprecation needed** - No backwards compatibility required

### Non-Breaking Changes

- Clarification of instructions
- Additional error handling
- Output format improvements
- Performance optimizations

### Change Review

When reviewing command file changes:

- Verify Prettier was run (check git diff formatting)
- Test command execution locally
- Ensure instructions are clear and complete
- Check for error handling gaps

## Real-World Examples

### Good Command File

```markdown
# /erk:plan-save

Save the current plan to GitHub as an issue.

## Prerequisites

- Must be in plan mode
- GitHub CLI authenticated

## Usage

\`\`\`bash
/erk:plan-save [--objective-issue=<number>]
\`\`\`

## Agent Instructions

### Step 1: Validate Environment

Run:
\`\`\`bash
erk exec plan-validate --format json
\`\`\`

If validation fails, display error and stop.

### Step 2: Save to GitHub

Run:
\`\`\`bash
erk exec plan-save-to-issue --format json --session-id="${CLAUDE_SESSION_ID}"
\`\`\`

Parse JSON output to get issue number.

### Step 3: Report Success

Output:
"Plan saved to issue #{issue_number}: {issue_title}"

## Related Commands

- /erk:plan-implement - Implement the saved plan
```

**Why it's good**:

- Clear prerequisites
- Explicit bash commands
- Error handling (validation fails → stop)
- Output format defined
- Related commands linked

### Bad Command File (Before Prettier)

```markdown
# /erk:plan-save

Save plan to GitHub

Prerequisites: plan mode

Instructions:
Run erk exec plan-save-to-issue and save the result
```

**Why it's bad**:

- No formatting (Prettier not run)
- Vague instructions ("save the result" - how?)
- No error handling
- No output format
- Missing structure

## Related Patterns

- [Slash Command Development](../commands/) - Full guide to command creation
- [CLI Development Patterns](../cli/) - CLI command best practices
- [Agent Delegation](../planning/agent-delegation.md) - When to delegate to subagents
