---
title: Turn Count as Performance Metric
read_when:
  - "profiling command or workflow performance"
  - "optimizing wall-clock latency"
  - "measuring before/after optimization impact"
  - "choosing between optimization strategies"
  - "investigating slow command execution"
---

# Turn Count as Performance Metric

## Core Insight

**Each LLM turn adds approximately 10-15 seconds of latency, regardless of token count.**

When optimizing command performance, focus on reducing turn count first. Token optimization provides marginal benefit compared to turn reduction.

## Why Turn Count Dominates

### Latency Sources

- **Per-turn overhead**: API round-trip, model initialization, response streaming
- **Network latency**: Consistent per-request, independent of payload size
- **Model processing**: Scales with tokens, but base latency is per-turn

### Real-World Example

`objective-update-with-landed-pr` optimization:

| Metric             | Before (4 turns) | After (2 turns) | Savings |
| ------------------ | ---------------- | --------------- | ------- |
| Wall-clock time    | 40-60s           | 15-23s          | 46-62%  |
| Token count        | ~8K              | ~6K             | 25%     |
| Cost (using Haiku) | ~$0.004          | ~$0.0004        | 90%     |

**Key observation**: 50% turn reduction → 50% wall-clock savings, not 25% token reduction.

## Profiling Methodology

### Step 1: Count Current Turns

Identify each LLM invocation in the workflow:

```
Turn 1: Load skill
Turn 2: Analyze input
Turn 3: Compose output
Turn 4: Validate result
→ Total: 4 turns
```

### Step 2: Identify Fusible Steps

Look for:

- Sequential operations with no branching logic
- Mechanical work (template composition, formatting)
- Steps where skill/context could be embedded instead of loaded
- Validation that could be done by analyzing output (self-validation)

### Step 3: Estimate Turn Reduction

Calculate potential savings:

```
Fusible turns × 10-15s = Expected wall-clock savings
```

### Step 4: Measure After Optimization

Compare actual turn count:

```
Before: 4 turns → ~50s
After: 2 turns → ~20s
Savings: 50% turn reduction → ~50% time reduction
```

## Optimization Strategies by Turn Reduction

### High-Impact (2+ turns saved)

- **Subagent delegation** - Fuse multiple sequential turns into one
- **Context embedding** - Replace "load skill" turn with embedded templates
- **Self-validation** - Eliminate "re-fetch to validate" turn

### Medium-Impact (1 turn saved)

- **Batch operations** - Combine multiple API calls into one turn
- **Prompt optimization** - Reduce need for clarification turns
- **Caching** - Skip redundant fetch/load operations

### Low-Impact (<1 turn)

- **Token reduction** - Useful but marginal wall-clock benefit
- **Prompt compression** - Saves cost but not latency

## Anti-Patterns

❌ **Optimizing token count first** - 50% token reduction = small latency improvement
❌ **Premature parallelization** - Doesn't help sequential workflows
❌ **Caching without turn analysis** - May save tokens but not turns
✅ **Profile turn count first** - Understand where latency comes from
✅ **Target turn reduction** - Fuse sequential operations
✅ **Measure wall-clock time** - Validate optimization impact

## Decision Framework

Before optimizing a command:

1. **Profile current turn count** - How many LLM invocations?
2. **Estimate turn reduction potential** - How many can be fused?
3. **Calculate expected savings** - Turns × 10-15s
4. **Compare to implementation cost** - Worth the effort?
5. **Measure after optimization** - Did we hit target?

## Examples

### 4-turn → 2-turn Optimization

```
Before: 40-60s (load, analyze, compose, validate)
After: 15-23s (fetch context, delegate to Haiku)
Savings: 46-62% wall-clock time
```

### 3-turn → 1-turn Optimization

```
Before: 30-45s (fetch, process, write)
After: 10-15s (batch fetch+process+write)
Savings: 60-70% wall-clock time
```

### Token-Only Optimization (No Turn Change)

```
Before: 20s (1 turn, 10K tokens)
After: 18s (1 turn, 5K tokens)
Savings: 10% wall-clock time (marginal)
```

## Related Patterns

- [Haiku Subagent Delegation](../architecture/subagent-delegation-for-optimization.md) - How to reduce turns via delegation
- [Subagent Self-Validation](../architecture/subagent-self-validation.md) - Eliminate validation turns
- [Subagent Prompt Structure](../architecture/subagent-prompt-structure.md) - Embed context to skip load turns

## Measurement Tools

### Manual Profiling

Count LLM turns in Claude Code session:

1. Review conversation history
2. Count agent responses (each response = 1 turn)
3. Identify sequential vs parallel turns

### Automated Profiling

Use session analysis:

```bash
erk exec analyze-session --metric turn-count
```

## Future Work

- Automated turn-count profiling in CI
- Turn-count budgets for command performance targets
- Dashboard showing turn-count distribution across commands
