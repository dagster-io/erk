---
title: Agent Output Routing Strategies
read_when:
  - "deciding how agents should receive and produce outputs"
  - "designing multi-agent orchestration prompts"
  - "choosing between embedded-prompt and agent-file routing"
tripwires:
  - action: "designing output routing for a multi-agent workflow"
    warning: "Choose between embedded-prompt routing (in orchestrator Task prompts) and agent-file routing (in agent definitions). See this doc for the decision framework."
---

# Agent Output Routing Strategies

When orchestrating multiple agents, output routing determines how each agent receives its inputs and where it writes its results. Two primary strategies exist.

## Embedded-Prompt Routing

Output paths and input references are specified in the orchestrator's `Task` prompt at invocation time:

```
Analyze the session at {session_path}.
Write your analysis to {output_path}.
```

**When to use**: Reusable agents that may be invoked in different workflows with different routing needs. The orchestrator controls the data flow.

**Advantages**:

- Agents remain generic and reusable
- Orchestrator has full control over data flow
- Easy to change routing without modifying agent definitions

**Disadvantages**:

- Orchestrator prompts become longer
- Routing logic is scattered across Task calls

## Agent-File Routing

Output paths and conventions are baked into the agent definition file:

```yaml
# In .claude/agents/my-analyzer.md
Write results to .erk/scratch/analysis.md
```

**When to use**: Single-purpose agents that always produce the same output in the same location. The agent owns its output contract.

**Advantages**:

- Agent is self-contained
- Orchestrator prompts stay concise
- Output location is documented in one place

**Disadvantages**:

- Agent is coupled to a specific workflow
- Harder to reuse in different contexts

## Decision Framework

| Factor                  | Embedded-Prompt        | Agent-File            |
| ----------------------- | ---------------------- | --------------------- |
| Agent reusability       | High                   | Low                   |
| Orchestrator complexity | Higher                 | Lower                 |
| Output flexibility      | Dynamic per invocation | Fixed                 |
| Best for                | Multi-workflow agents  | Single-purpose agents |

## Canonical Example

The `/erk:learn` command uses embedded-prompt routing: each analysis agent receives input and output paths via its Task prompt, allowing the same agents to be reused across different learn workflows.

## Related Documentation

- [Context Efficiency Patterns](../architecture/context-efficiency.md) — Avoiding content relay anti-pattern
- [Exploration Strategies](exploration-strategies.md) — Two-stage Explore-then-Plan workflow
