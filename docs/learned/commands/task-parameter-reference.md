---
title: Task Tool Parameter Reference
read_when:
  - "spawning subagents with Task tool"
  - "specifying model for Task invocations"
  - "understanding Task tool capabilities"
  - "writing slash commands that use Task"
tripwires:
  - action: "adding new Task invocation to any command file"
    warning: "Always include explicit `model` parameter (haiku/sonnet/opus); don't rely on defaults. Model selection affects cost and quality."
---

# Task Tool Parameter Reference

The Task tool spawns subagents to handle complex tasks autonomously. This reference covers the key parameters and best practices.

## Model Parameter

The `model` parameter specifies which Claude model the subagent should use:

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",  # or "sonnet" or "opus"
  description: "...",
  prompt: "..."
)
```

### Available Models

| Model  | Cost   | Speed  | Use For                                                        |
| ------ | ------ | ------ | -------------------------------------------------------------- |
| haiku  | Low    | Fast   | Orchestration, extraction, classification, iterative execution |
| sonnet | Medium | Medium | Complex analysis, code review, decision-making                 |
| opus   | High   | Slower | Complex reasoning, novel problem solving, creative synthesis   |

### When to Use Each Model

**Haiku** - Best for mechanical tasks:

- Parsing and extracting structured data
- Classification and categorization
- Running iterative commands (devrun agent)
- Tasks with clear, rule-based logic

**Sonnet** - Best for analytical tasks:

- Code review and analysis
- Debugging complex issues
- Tasks requiring moderate reasoning

**Opus** - Best for creative/complex tasks:

- Writing documentation or explanatory content
- Architectural design decisions
- Novel problem solving
- Multi-step planning with trade-offs

## Best Practices

1. **Always specify explicitly** - Don't rely on defaults; model selection affects cost and quality
2. **Match to task complexity** - Use haiku for mechanical tasks, opus for synthesis
3. **Consider parallel execution** - Haiku saves significantly when multiple agents run simultaneously
4. **Document your choice** - Add a comment explaining why you chose the model

## Background Execution

Use `run_in_background: true` for parallel agent execution:

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze session",
  prompt: "..."
)
```

Then retrieve results with `TaskOutput(task_id: <id>, block: true)`.

## Subagent Types

The `subagent_type` parameter selects the agent's capabilities:

| Type            | Purpose                                   |
| --------------- | ----------------------------------------- |
| general-purpose | Multi-purpose agent with full tool access |
| Explore         | Fast codebase exploration                 |
| Plan            | Software architecture and planning        |
| devrun          | Execute dev tools (pytest, ruff, etc.)    |

See AGENTS.md for the full list of available subagent types.

## Related Topics

- [Model Selection for Learn Workflow](../planning/model-selection-learn-workflow.md) - Tier-based model selection pattern
- [Command Optimization Patterns](optimization-patterns.md) - General command authoring patterns
