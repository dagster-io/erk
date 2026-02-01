---
title: Haiku Subagent Delegation for Optimization
read_when:
  - "optimizing command performance or wall-clock latency"
  - "considering subagent delegation for workflow optimization"
  - "implementing commands that perform mechanical or template-driven work"
  - "refactoring multi-turn workflows"
  - "choosing between direct execution and Task tool delegation"
tripwires:
  - action: "implementing deterministic command logic with multiple sequential turns"
    warning: "Consider Task delegation with Haiku for mechanical, template-driven work. Turn count dominates wall-clock latency (each turn adds 10-15s). This is a missed optimization opportunity."
---

# Haiku Subagent Delegation for Optimization

## Overview

When optimizing command performance, **turn count is the dominant factor in wall-clock latency**, not token count. Each LLM turn adds approximately 10-15 seconds of latency regardless of how many tokens are processed. By delegating mechanical, template-driven work to a Haiku subagent, you can fuse multiple sequential turns into a single subagent turn, achieving significant wall-clock time savings.

## Performance Impact

Real-world optimization of `objective-update-with-landed-pr`:

- **Before**: 4 turns (40-60s) - load skill, analyze/compose comment, update roadmap, validate
- **After**: 2 turns (15-23s) - fetch context JSON, delegate to Haiku subagent
- **Savings**: 46-62% wall-clock time reduction
- **Cost**: Haiku is ~10x cheaper than Sonnet, ~30x cheaper than Opus

## When to Use Haiku Delegation

Delegate to Haiku subagents when work is:

- **Deterministic**: Clear rules, no creative reasoning required
- **Template-driven**: Composition from structured input (JSON, markdown templates)
- **Mechanical**: String manipulation, formatting, validation against known patterns
- **Multi-step**: Multiple sequential operations that can be fused into one turn

## Implementation Pattern

### Parent Agent Responsibilities

1. **Fetch context** - Gather all data needed for the subagent
2. **Structure input** - Convert to JSON or structured format
3. **Delegate** - Launch Haiku subagent with complete context
4. **Handle result** - Process subagent output and continue workflow

### Subagent Responsibilities

1. **Validate input** - Ensure all required data is present
2. **Execute work** - Perform mechanical operations
3. **Self-validate** - Check output against rules without re-fetching
4. **Return result** - Structured output for parent to process

## Example: objective-update-with-landed-pr Optimization

### Before (4 turns, 40-60s)

```
Turn 1: Parent loads skill
Turn 2: Parent analyzes PR, composes action comment
Turn 3: Parent updates objective roadmap body
Turn 4: Parent re-fetches objective via GitHub API to validate
```

### After (2 turns, 15-23s)

```
Turn 1: Parent fetches context JSON (PR data, objective data, rules)
Turn 2: Haiku subagent:
  - Composes action comment from PR context
  - Updates objective roadmap body
  - Self-validates by counting steps
  - Writes changes via GitHub API
```

### Key Optimization Techniques

1. **Context Embedding**: Parent embeds all necessary data in subagent prompt

   ```json
   {
     "pr": {...},
     "objective": {...},
     "templates": {...},
     "rules": [...]
   }
   ```

2. **Self-Validation**: Subagent validates by analyzing composed content
   - Counts steps in roadmap body it just wrote
   - Checks against expected patterns
   - No need to re-fetch from GitHub API

3. **Turn Fusion**: Multiple parent operations become single subagent turn
   - Load skill → embedded in prompt
   - Analyze → subagent does it
   - Compose → subagent does it
   - Validate → subagent self-validates
   - Write → subagent does it

## Implementation Checklist

When delegating to Haiku for optimization:

- [ ] Work is deterministic and template-driven
- [ ] All context is fetched by parent and embedded in prompt
- [ ] Subagent prompt includes templates, rules, success criteria
- [ ] Subagent can self-validate without re-fetching
- [ ] Expected to save at least 1 turn (10-15s)
- [ ] Cost reduction justifies implementation effort

## Common Mistakes

❌ **Delegating creative/reasoning work to Haiku** - Use Sonnet for reasoning
❌ **Incomplete context embedding** - Subagent will re-fetch or fail silently
❌ **Optimizing tokens without considering turns** - Marginal benefit
❌ **Re-fetching for validation when subagent has context** - Wastes API call

## Related Patterns

- [Subagent Self-Validation](subagent-self-validation.md) - How subagents validate output
- [Subagent Prompt Structure](subagent-prompt-structure.md) - How to structure prompts
- [Turn Count Profiling](../optimization/turn-count-profiling.md) - How to measure performance
- [Subagent Model Selection](../reference/subagent-model-selection.md) - When to use each model

## Future Optimization Candidates

Look for these patterns in existing commands:

- Multiple sequential LLM turns
- Load skill → analyze → compose → validate workflows
- GitHub API read → process → write sequences
- Template-based composition tasks
