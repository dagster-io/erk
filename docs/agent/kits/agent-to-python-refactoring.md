---
title: Agent-to-Python Refactoring Pattern
read_when:
  - "refactoring large agents to Python"
  - "agent has more than 300 lines"
  - "agent token usage is too high"
  - "making agents more testable"
  - "reducing mechanical operations in agents"
---

# Agent-to-Python Refactoring Pattern

When an agent grows too large (300+ lines) or contains mostly mechanical operations, consider refactoring to Python with a minimal agent.

## Signs You Need This Pattern

1. Agent has >300 lines of markdown
2. Most operations are bash commands (mechanical, not semantic)
3. Error handling is rule-based (not requiring judgment)
4. String parsing/formatting dominates the agent
5. Token cost per invocation is high (>5000 tokens)

## The Two-Phase Architecture

Refactor large agents into:

```
Slash Command → Preflight (Python) → AI Analysis (Minimal Agent) → Finalize (Python)
```

### Preflight Phase (Python)

- Authentication checks
- Data gathering (diffs, status)
- File operations
- Returns structured result for agent

### AI Analysis Phase (Agent)

- Only semantic operations
- Diff analysis, content generation
- Receives structured input, outputs structured result
- Target: <100 lines

### Finalize Phase (Python)

- Apply AI-generated content
- Update external systems (PRs, issues)
- Cleanup operations

## Implementation Checklist

1. Identify mechanical vs semantic operations
2. Create Python operations module in `erk_shared/integrations/<name>/`
3. Create kit CLI commands for preflight/finalize
4. Write minimal agent for semantic work only
5. Update slash command to orchestrate phases
6. Add tests with FakeGit/FakeGitHub

## Example: git-branch-submitter

**Before:** 442 lines, ~7500 tokens, untestable
**After:** ~60 lines agent + Python operations, ~2500 tokens, fully testable

See: `erk_shared/integrations/git_pr/` for implementation
