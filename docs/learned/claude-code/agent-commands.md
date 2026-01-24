---
title: Claude Code Agent Command Patterns
read_when:
  - "creating Claude Code agent commands"
  - "implementing conversation-context extraction"
  - "building commands that search conversation history"
tripwires:
  - action: "creating Claude Code agent commands in .claude/commands/"
    warning: "Filenames MUST match the command name for discoverability."
---

# Claude Code Agent Command Patterns

Agent commands are markdown files in `.claude/commands/` that Claude Code executes. They enable AI-powered operations that require conversation context, natural language understanding, or multi-step reasoning.

## Conversation-Context Extraction Pattern

Several commands extract references (issue numbers, PR numbers, URLs) from conversation history. This pattern enables commands like `/erk:plan-submit`, `/erk:pr-address-remote`, and `/erk:prepare` to automatically find the relevant artifact without requiring explicit arguments.

### Key Principles

1. **Search bottom-to-top**: Search from the most recent messages first (recency bias)
2. **Priority-ordered patterns**: Match higher-priority patterns before lower-priority ones
3. **Multi-format support**: Handle URLs, abbreviated references (`#123`), and contextual mentions
4. **Graceful failure**: Report clear errors when the artifact isn't found

### Pattern Structure

A typical extraction section in an agent command:

```markdown
## Finding the [Artifact]

Search the conversation from bottom to top for these patterns (in priority order):

1. **Primary pattern**: [Most specific/reliable format]
2. **Secondary pattern**: [Alternative format]
3. **Fallback pattern**: [Looser match if needed]

Extract the [identifier] from the most recent match.
```

### Common Extraction Patterns

**GitHub Issues:**

1. `**Issue:** https://github.com/.../issues/<number>` (from plan-save output)
2. `https://github.com/<owner>/<repo>/issues/<number>` (full URL)
3. `#<number>` with issue context (abbreviated reference)

**Pull Requests:**

1. `https://github.com/<owner>/<repo>/pull/<number>` (full URL)
2. `PR: https://github.com/.../pull/<number>` (from PR creation output)
3. `Draft PR #<number> created` (from creation confirmation)
4. `PR #<number>` with contextual mention

### Example: PR Extraction (from `/erk:pr-address-remote`)

```markdown
## Finding the PR

Search the conversation from bottom to top for these patterns (in priority order):

1. **PR URL**: `https://github.com/<owner>/<repo>/pull/<number>`
2. **PR creation output**: `PR: https://github.com/.../pull/<number>` or `Draft PR #<number> created`
3. **PR reference with context**: `PR #<number>` (e.g., "PR #5846", "submitted PR #5846")

Extract the PR number from the most recent match.
```

### Error Handling

Always include clear error messages:

```markdown
## Error Cases

- **No [artifact] found in conversation**: Report "[Specific message with next action]"
- **[erk command] fails**: Display the error output from the command
```

## Agent Command vs CLI Command

See [Agent Command vs CLI Command Boundaries](../architecture/command-boundaries.md) for deciding when to use agent commands versus CLI commands.

**Use agent commands when:**

- Natural language analysis or understanding is required
- Multi-step reasoning based on context
- The operation needs conversation history

**Use CLI commands when:**

- The operation is deterministic
- Pure data transformation
- External tool orchestration (git, gh, gt)

## Related Topics

- [command-boundaries.md](../architecture/command-boundaries.md) - CLI vs agent decisions
- [claude-executor-patterns.md](../architecture/claude-executor-patterns.md) - ClaudeExecutor usage
