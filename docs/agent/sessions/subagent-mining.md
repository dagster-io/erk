---
title: Mining Subagent Outputs for Documentation Gaps
read_when:
  - "analyzing sessions for extraction plans"
  - "identifying documentation gaps from agent outputs"
  - "reviewing Task tool invocations"
---

# Mining Subagent Outputs for Documentation Gaps

When analyzing sessions for extraction plans, subagents (Explore, Plan) often contain the most valuable discoveries.

## Finding Subagent Invocations

Look for `<tool_use name="Task">` blocks in session logs:

```xml
<tool_use name="Task" id="toolu_...">
  <param name="description">Explore metadata block system</param>
  <param name="subagent_type">Explore</param>
  <param name="prompt">Explore how metadata blocks work...</param>
</tool_use>
```

## Reading Agent Output

Each Task returns detailed output. Look for:

**Explore agents:**

- Files discovered and their purposes
- Patterns found in codebase
- Architectural decisions inferred
- Connections between components

**Plan agents:**

- Approaches considered
- Why alternatives were rejected
- Design decisions and tradeoffs
- Constraints discovered

## Example: Mining for Documentation Gaps

**Raw Agent Output:**

> "The existing provider pattern in data/provider.py uses ABC with abstract methods.
> This follows erk's fake-driven testing pattern where FakeProvider implements the same interface."

**What This Tells Us:**

- **Confirms** ABC pattern is already documented (not a gap)
- **Confirms** fake-driven-testing skill connection exists
- **May indicate gap** if the agent had to discover this (wasn't obvious from routing)

## Anti-Patterns

**Don't just summarize:** ❌ "Agent explored the codebase"
**Extract insights:** ✅ "Agent discovered metadata blocks use YAML frontmatter with strict schema validation"

**Don't treat as black box:** ❌ "Agent figured it out"
**Mine the reasoning:** ✅ "Agent compared approaches: inline vs external config, chose inline for atomicity"

## Related

- Session Context Mining: [docs/agent/sessions/context-analysis.md](context-analysis.md)
- Extraction Plan Creation: `.claude/commands/erk/create-extraction-plan.md`
