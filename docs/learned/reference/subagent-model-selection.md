---
title: Subagent Model Selection Heuristic
read_when:
  - "choosing model for Task tool delegation"
  - "optimizing subagent cost vs quality tradeoffs"
  - "implementing new command with subagent delegation"
  - "deciding between Haiku, Sonnet, and Opus for subagents"
  - "balancing performance and cost in subagent workflows"
---

# Subagent Model Selection Heuristic

## Overview

When delegating work to subagents via the Task tool, choose the model based on task characteristics. Different models offer different cost/speed/quality tradeoffs.

## Model Characteristics

| Model      | Relative Cost | Speed   | Best For                                                        |
| ---------- | ------------- | ------- | --------------------------------------------------------------- |
| **Haiku**  | 1x (baseline) | Fastest | Template composition, mechanical work, deterministic tasks      |
| **Sonnet** | ~10x          | Medium  | Reasoning, analysis, non-trivial decisions, code generation     |
| **Opus**   | ~30x          | Slowest | Creative work, complex reasoning, critical quality requirements |

## Decision Matrix

### Use Haiku When:

- **Template-driven composition** - Filling in markdown/JSON templates
- **Mechanical operations** - String manipulation, formatting, validation
- **Deterministic tasks** - Clear rules, no creative decisions
- **High-volume operations** - Cost matters, quality is predictable
- **Self-validation possible** - Can validate output without external checks

**Examples**:

- Compose action comment from PR data
- Update objective roadmap body with completed steps
- Format CLI output from JSON data
- Validate structure against known patterns

### Use Sonnet When:

- **Non-trivial reasoning** - Analyzing patterns, making decisions
- **Code generation** - Writing Python, shell scripts, complex logic
- **Debugging** - Analyzing errors, suggesting fixes
- **Exploration** - Understanding codebase, finding patterns
- **Medium complexity** - More than template filling, less than research

**Examples**:

- Analyze session logs to extract insights
- Generate implementation plan from requirements
- Debug failing tests and suggest fixes
- Explore codebase to understand architecture

### Use Opus When:

- **Creative work** - Novel solutions, architectural design
- **Complex reasoning** - Multi-step analysis, tradeoff evaluation
- **Critical quality** - User-facing docs, PR descriptions, architectural decisions
- **Research tasks** - Deep exploration, synthesis from multiple sources

**Examples**:

- Design new system architecture
- Write user-facing documentation
- Synthesize insights from multiple sessions
- Evaluate complex architectural tradeoffs

## Default Strategy

**Start with Haiku, escalate only when needed.**

1. **First attempt**: Try Haiku if task seems mechanical
2. **Evaluate output**: If quality is insufficient, escalate to Sonnet
3. **Cost-benefit**: Only use Opus when quality justifies 30x cost

## Cost-Benefit Analysis

### Example: objective-update-with-landed-pr

**Task**: Compose action comment, update roadmap body.

**Analysis**:

- Template-driven: ✅ (action comment, roadmap format)
- Mechanical: ✅ (string substitution, markdown composition)
- Deterministic: ✅ (clear rules, no creativity needed)
- Self-validating: ✅ (count steps, pattern matching)

**Decision**: Use Haiku.

**Cost savings**: Haiku (~$0.0004) vs Sonnet (~$0.004) = 10x cheaper.

**Quality**: Template composition doesn't benefit from Sonnet reasoning.

### Example: Analyze Session for Insights

**Task**: Extract patterns, decisions, and insights from session logs.

**Analysis**:

- Template-driven: ❌ (free-form analysis)
- Mechanical: ❌ (requires reasoning)
- Deterministic: ❌ (insights not predictable)
- Self-validating: ⚠️ (hard to validate quality)

**Decision**: Use Sonnet.

**Quality requirement**: Insights must be accurate and relevant.

**Cost justification**: 10x cost acceptable for quality-critical analysis.

### Example: Design New Architecture

**Task**: Design plan-oriented workflow architecture.

**Analysis**:

- Creative: ✅ (novel solution)
- Complex reasoning: ✅ (tradeoff evaluation)
- Critical quality: ✅ (affects entire system)
- Research needed: ✅ (explore alternatives)

**Decision**: Use Opus.

**Quality requirement**: Architecture decisions are expensive to change.

**Cost justification**: 30x cost acceptable for critical design work.

## Performance Considerations

### Turn Count vs Model Choice

**Haiku delegation reduces turn count** → larger performance impact than model choice.

Example:

- 4 Sonnet turns: 40-60s
- 2 turns (1 Sonnet + 1 Haiku): 15-23s

**Key insight**: Turn reduction (50%) matters more than model speed difference (~20%).

### When Model Choice Doesn't Matter

If task is single-turn and quality requirements are clear:

- Haiku: ~5-10s
- Sonnet: ~10-15s
- Opus: ~15-20s

**Difference**: 5-10s, often acceptable for quality improvement.

If task is multi-turn and can be fused:

- 4 Sonnet turns: 40-60s
- 1 Haiku turn: 5-10s

**Difference**: 35-50s, significant performance gain.

## Common Mistakes

❌ **Using Sonnet by default** - 10x cost, often unnecessary
❌ **Haiku for complex reasoning** - Quality suffers, false economy
❌ **Opus for mechanical work** - 30x cost, no quality benefit
❌ **Ignoring turn count** - Model choice has less impact than turn reduction
✅ **Start with Haiku** - Escalate only when quality requires it
✅ **Optimize turn count first** - Then consider model choice
✅ **Measure quality** - Validate Haiku output before committing to pattern

## Decision Flowchart

```
Is the task template-driven and deterministic?
├─ Yes → Use Haiku
└─ No
   ├─ Is reasoning or code generation required?
   │  ├─ Yes → Use Sonnet
   │  └─ No → Use Opus (creative/critical work)
   └─ Is quality critical and cost acceptable?
      ├─ Yes → Use Opus
      └─ No → Use Sonnet
```

## Model Upgrade Path

1. **Prototype with Haiku** - See if quality is acceptable
2. **Measure quality** - Does output meet requirements?
3. **Upgrade to Sonnet** - If reasoning/complexity needed
4. **Upgrade to Opus** - Only if Sonnet quality insufficient

## Real-World Examples

### Haiku Success: objective-update-with-landed-pr

- **Task**: Template composition, validation
- **Result**: 90% cost savings, same quality as Sonnet
- **Lesson**: Mechanical work doesn't need reasoning

### Sonnet Success: Session Analysis

- **Task**: Extract patterns from logs
- **Result**: High-quality insights, 10x cost justified
- **Lesson**: Reasoning tasks benefit from Sonnet

### Opus Success: Architecture Design

- **Task**: Design new workflow system
- **Result**: Novel solution, 30x cost justified
- **Lesson**: Creative work benefits from Opus

## Related Patterns

- [Subagent Delegation for Optimization](../architecture/subagent-delegation-for-optimization.md) - When to delegate
- [Turn Count Profiling](../optimization/turn-count-profiling.md) - Measuring performance impact
- [Subagent Prompt Structure](../architecture/subagent-prompt-structure.md) - How to structure prompts
