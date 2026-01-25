---
title: Context Fork Feature for Skills
read_when:
  - "creating skills that need context isolation"
  - "building skills that fetch large data"
  - "implementing skills that should run in subagents"
  - "reducing context window usage with skills"
tripwires:
  - action: "creating a skill with context: fork without explicit task instructions"
    warning: "Skills with context: fork need actionable task prompts. Guidelines-only skills return empty output."
---

# Context Fork Feature for Skills

## Overview

The `context: fork` frontmatter option (added in Claude Code 2.1.0) runs a skill in an isolated subagent context. The skill content becomes the prompt driving the subagent, which runs without access to conversation history.

## When to Use

Use `context: fork` when:

- Fetching large data (API responses, PR comments) that would pollute main context
- Running multi-step operations with verbose intermediate output
- Need deterministic output format without main conversation influence
- Implementing "fetch and classify" patterns

Do NOT use `context: fork` when:

- Skill contains only guidelines/conventions (no actionable task)
- Skill needs conversation context to work
- Skill is reference material Claude should apply inline

## Frontmatter Options

```yaml
---
name: my-skill
description: What this skill does
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

1. Skill fetches data (API calls, file reads)
2. Skill classifies/processes data
3. Skill outputs structured JSON
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

## Invoking Forked Skills

From commands or conversation, invoke with:

```
/skill-name [arguments]
```

Arguments are available to the skill via `$ARGUMENTS`.

## Important Considerations

1. **Explicit instructions required**: The skill content IS the task. Guidelines-only content produces empty or unhelpful output.

2. **No conversation history**: Subagent starts fresh. Include all needed context in skill content.

3. **Output format**: Define explicit output format. Subagent cannot infer what main conversation needs.

4. **Arguments via $ARGUMENTS**: Pass flags through skill arguments, not conversation context.

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
