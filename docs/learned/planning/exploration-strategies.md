---
title: Exploration Strategies
read_when:
  - "deciding when to use Explore agents vs direct searches"
  - "planning a two-stage explore-then-plan workflow"
  - "gathering codebase context before entering plan mode"
---

# Exploration Strategies

Effective plans require thorough codebase understanding before plan creation begins. This document covers the two-stage Explore-then-Plan workflow.

## Two-Stage Workflow: Explore Then Plan

1. **Explore phase**: Launch Explore agents to gather facts about the codebase — file locations, existing patterns, API surfaces, test structures
2. **Plan phase**: Enter plan mode with full context and write the plan immediately without further exploration

### Why Two Stages?

Plan mode is optimized for plan _writing_, not _discovery_. Mixing exploration into planning fragments the session with mechanical file reads and search operations. By front-loading exploration, the planning phase stays focused and coherent.

### Explore Phase Tactics

- Use parallel Explore agents for independent questions ("What does the gateway layer look like?" and "How are tests structured?" can run simultaneously)
- Search `docs/learned/` first — documented patterns are faster and more reliable than re-discovering from source
- Read actual source files to verify documentation is current

### Plan Phase Entry

Enter plan mode only when you can answer:

- What files need to change?
- What existing patterns should be followed?
- What test patterns exist for this area?
- Are there documented pitfalls or tripwires?

## When to Skip the Explore Phase

- The task is well-understood and affects a small, known set of files
- Documentation already covers the relevant patterns completely
- The task is a direct follow-up to recent work in the same area

## Related Documentation

- [Planning Patterns](planning-patterns.md) — Pre-plan context gathering patterns
- [Agent Output Routing Strategies](agent-output-routing-strategies.md) — Routing for multi-agent workflows
