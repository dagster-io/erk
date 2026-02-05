---
title: Context Fork Feature
read_when:
  - "creating skills that need context isolation"
  - "creating commands that need context isolation"
  - "building skills or commands that fetch large data"
  - "implementing skills or commands that should run in subagents"
  - "reducing context window usage with skills or commands"
tripwires:
  - action: "creating a skill or command with context: fork without explicit task instructions"
    warning: "Skills/commands with context: fork need actionable task prompts. Guidelines-only content returns empty output."
---

# Context Fork Feature

## Overview

The `context: fork` frontmatter option (added in Claude Code 2.1.0) runs a skill or command in an isolated subagent context. Since Claude Code 2.1.0, commands in `.claude/commands/` support the same frontmatter options as skills, including `context: fork`. The skill/command content becomes the prompt driving the subagent, which runs without access to conversation history.

## When to Use

Use `context: fork` when:

- Fetching large data (API responses, PR comments) that would pollute main context
- Running multi-step operations with verbose intermediate output
- Need deterministic output format without main conversation influence
- Implementing "fetch and classify" patterns

Do NOT use `context: fork` when:

- Skill/command contains only guidelines/conventions (no actionable task)
- Skill/command needs conversation context to work
- Skill/command is reference material Claude should apply inline

## Frontmatter Options

Since Claude Code 2.1.0, files in `.claude/commands/` support the same frontmatter as skills:

```yaml
---
name: my-skill # Optional for commands (inferred from filename)
description: What this skill/command does
context: fork # Run in isolated subagent
agent: general-purpose # Which agent type (optional)
argument-hint: "[--flag]" # Help text for arguments
---
```

### Agent Types

- `general-purpose`: Default, full tool access
- `Explore`: Read-only tools (Glob, Grep, Read, Bash)
- `Plan`: Planning-focused agent
- Custom agents from `.claude/agents/`

## Pattern: Fetch and Classify

The canonical use case is fetching large data and returning compact structured output:

1. Skill/command fetches data (API calls, file reads)
2. Skill/command classifies/processes data
3. Skill/command outputs structured JSON
4. Main conversation parses JSON and acts on it

**Token savings**: ~65-70% reduction vs inline fetch (raw JSON never enters main context).

## Example: PR Feedback Classifier

```yaml
---
name: pr-feedback-classifier
description: Fetch and classify PR review feedback
context: fork
agent: general-purpose
argument-hint: "[--include-resolved]"
---

# PR Feedback Classifier

Fetch PR comments and return structured JSON.

## Steps
1. Get branch and PR info
2. Fetch comments via erk exec commands
3. Classify each comment
4. Output JSON

## Output Format
{
  "success": true,
  "actionable_threads": [
    {"thread_id": "PRRT_xxx", "action_summary": "...", "complexity": "local"}
  ],
  "batches": [...]
}
```

## Invoking Forked Skills and Commands

From conversation, invoke with:

```
/skill-name [arguments]
/command-name [arguments]
```

Arguments are available to the skill/command via `$ARGUMENTS`.

## Important Considerations

1. **Explicit instructions required**: The skill/command content IS the task. Guidelines-only content produces empty or unhelpful output.

2. **No conversation history**: Subagent starts fresh. Include all needed context in skill/command content.

3. **Output format**: Define explicit output format. Subagent cannot infer what main conversation needs.

4. **Arguments via $ARGUMENTS**: Pass flags through skill/command arguments, not conversation context.

5. **JSON output**: For structured data, specify "output ONLY JSON" to avoid prose wrapper.

## Comparison with Task Delegation

| Aspect          | `context: fork`               | Manual Task        |
| --------------- | ----------------------------- | ------------------ |
| Declaration     | Frontmatter                   | Inline in command  |
| Reusability     | Skill can be invoked anywhere | One-off in command |
| Prompt location | Skill file                    | Command file       |
| Maintenance     | Centralized                   | Duplicated         |
| Dynamic content | Via $ARGUMENTS                | Full flexibility   |

**Prefer `context: fork`** for reusable classification/fetch patterns.

**Use manual Task** for one-off operations or when dynamic prompt content is needed.

## Related Documentation

- [Task Context Isolation Pattern](../architecture/task-context-isolation.md) - Manual Task delegation approach
- [Command-Agent Delegation](../planning/agent-delegation.md) - Full agent delegation patterns
