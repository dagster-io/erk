---
title: Multi-Layer Exploration Strategies
read_when:
  - "planning an implementation that requires understanding multiple code areas"
  - "using nested Task(Explore) agents for information gathering"
  - "designing planning workflows that need comprehensive context"
---

# Multi-Layer Exploration Strategies

## The Pattern

Before entering Plan mode for complex tasks, use nested Task(Explore) agents to gather comprehensive information from multiple code areas. Each Explore agent targets a different aspect of the system, and their results inform the planning phase.

## When to Use

Use multi-layer exploration when:

- The task spans multiple files or subsystems
- Understanding the current implementation is required before planning changes
- Multiple independent questions need answering before a coherent plan can be formed

## Example: Context Efficiency Diagnosis

The planning session for PR #6949 used two nested Explore agents before entering Plan mode:

1. First Explore agent: Analyzed the learn command implementation to understand where context consumption occurred
2. Second Explore agent: Examined agent definitions and the existing self-write precedent (tripwire-extractor)

The Explore agents gathered enough context to diagnose the content relay anti-pattern and calculate exact token overhead (6 agents x 2 copies x 5-15K = 60-180K tokens), which then informed the plan.

## Key Principle

Explore agents are cheap — they run at lower model tiers and their output stays in the planning context. The alternative (loading all files directly into the main conversation) is more expensive and less organized. Delegate exploration to subagents, then synthesize their findings into a coherent plan.

## Related Documentation

- [Agent Delegation](agent-delegation.md) — When to delegate to agents
- [Context Efficiency](../architecture/context-efficiency.md) — Why context management matters
