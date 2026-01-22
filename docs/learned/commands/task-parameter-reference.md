---
title: Task Tool Parameter Reference
read_when:
  - "spawning subagents with Task tool"
  - "specifying model for Task invocations"
  - "understanding Task tool capabilities"
tripwires:
  - action: "Modifying learn command to add/remove/reorder Task invocations"
    warning: "Before applying model parameters, verify tier structure (parallel vs sequential). Misplacing haiku task in final synthesis tier degrades quality. Reference: parallel tasks use haiku, sequential tier 1 uses haiku, sequential tier 2 uses opus."
  - action: "Adding new agents to learn workflow"
    warning: "Document input/output format clearly and test file passing integration. Architecture assumes stateless agents with file-based composition."
---

# Task Tool Parameter Reference

This document describes the parameters available when invoking the Task tool in Claude Code commands.

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

| Model  | Cost   | Speed  | Use For                                              |
| ------ | ------ | ------ | ---------------------------------------------------- |
| haiku  | Low    | Fast   | Orchestration, extraction, classification, iteration |
| sonnet | Medium | Medium | Complex analysis, code review, decision-making       |
| opus   | High   | Slower | Complex reasoning, novel problem solving, synthesis  |

### Best Practices

1. **Always specify explicitly** - Don't rely on defaults; model selection affects cost and quality
2. **Match to task complexity** - Use haiku for mechanical tasks, opus for synthesis
3. **Consider parallel execution** - Haiku saves significantly when multiple agents run simultaneously

## Other Parameters

### subagent_type

Specifies the agent type. Common values:

- `general-purpose` - Standard agent for most tasks
- `Explore` - Fast agent for codebase exploration
- `devrun` - Read-only agent for running dev tools

### run_in_background

When `true`, launches the agent without blocking. Use `TaskOutput` to retrieve results later.

```
Task(
  run_in_background: true,
  ...
)
```

### description

Short (3-5 word) description shown in status messages.

### prompt

The full instructions for the agent. Should include:

- Agent instructions file to load (e.g., `.claude/agents/learn/session-analyzer.md`)
- Input parameters the agent needs
- Expected output format

## Example: Multi-Agent Workflow

```
# Parallel tier - extract cheap
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze session",
  prompt: "Load .claude/agents/learn/session-analyzer.md and analyze..."
)

# Sequential tier - synthesize premium
Task(
  subagent_type: "general-purpose",
  model: "opus",
  description: "Synthesize plan",
  prompt: "Load .claude/agents/learn/plan-synthesizer.md and create..."
)
```

## Related Topics

- [Model Selection for Learn Workflow](../planning/model-selection-learn-workflow.md) - Tier-based model selection pattern
- [Agent Delegation](../planning/agent-delegation.md) - When to use subagents
