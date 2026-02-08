---
title: Defense-in-Depth Enforcement
read_when:
  - designing multi-layer validation or enforcement systems
  - implementing critical rules across multiple components
  - understanding why erk uses redundant enforcement mechanisms
tripwires:
  - action: "Rely solely on agent-level enforcement for critical rules"
    warning: "Add skill-level and PR-level enforcement layers. Only workflow/CI enforcement is truly reliable."
    score: 7
---

# Defense-in-Depth Enforcement

Defense-in-depth enforcement uses multiple independent layers to enforce the same rule. Each layer catches violations the previous layers missed, creating resilient systems even when individual layers fail.

## The Pattern

For critical rules (those that cause bugs, tech debt, or maintenance burden when violated), implement enforcement at multiple independent layers:

```
Layer 1: Agent-level (guidance in agent prompts)
    ↓ (might be ignored, missed, or misinterpreted)
Layer 2: Skill-level (rules in loaded skills)
    ↓ (might not be loaded, or loaded too late)
Layer 3: PR-level (automated reviews, CI checks)
    ↓ (most reliable - runs deterministically on every PR)
```

Each layer operates independently. Violations caught at Layer 3 indicate that Layers 1 and 2 failed, but the system still prevents the problem from reaching production.

## Example: Verbatim Code Block Prevention

The verbatim code block prevention system illustrates defense-in-depth:

### Layer 1: Agent-Level (code-diff-analyzer agent)

**Location**: `.claude/agents/code-diff-analyzer/AGENT.md`

**Mechanism**: Agent analyzing PR diffs detects code blocks in `docs/learned/` and warns about verbatim copies

**Failure modes**:

- Agent not invoked for the PR
- Agent misinterprets what constitutes a "verbatim copy"
- Context limits prevent full diff analysis
- Agent warnings ignored by implementer

### Layer 2: Skill-Level (learned-docs skill)

**Location**: `.claude/skills/learned-docs/SKILL.md`

**Mechanism**: Skill loaded when writing docs instructs agent to avoid verbatim code, use source pointers instead

**Failure modes**:

- Skill not loaded during documentation session
- Skill loaded after code blocks already written
- Agent doesn't recognize the pattern as verbatim
- Agent prioritizes other guidance over skill rules

### Layer 3: PR-Level (learned-docs review)

**Location**: `.github/reviews/audit-pr-docs.md`

**Mechanism**: Automated review runs on every PR touching `docs/learned/`, posts inline comments for verbatim copies with exact source file and line numbers

**Failure modes**:

- Review disabled or broken
- False negatives in detection logic
- Detection logic not yet expanded to all languages (currently Python-only)

**Reliability**: Highest - runs deterministically, always active, provides actionable feedback

### Key Insight: Upstream Layers Can Be Under Development

<!-- Source: docs/learned/planning/reliability-patterns.md:38-61 -->

From [reliability-patterns.md](../planning/reliability-patterns.md:38-61):

> Only Layer 3 is truly reliable. Layers 1 and 2 serve as defense-in-depth but cannot be the sole mechanism for critical operations.

The defense-in-depth pattern allows you to:

1. **Deploy Layer 3 immediately** (automated PR checks)
2. **Develop Layers 1-2 incrementally** (agent and skill enhancements)
3. **Measure effectiveness** by tracking which layer catches violations

Upstream layers (1-2) reduce the burden on downstream layers (3) by catching most violations earlier, but downstream layers must always be present for critical rules.

## When to Use Defense-in-Depth

Apply this pattern when:

1. **Rule violations cause real problems**
   - Technical debt (stale code blocks)
   - Bugs (missing required fields)
   - Security issues (exposed credentials)
   - Breaking changes (API contract violations)

2. **Single-layer enforcement is unreliable**
   - Agent instructions can be missed or misinterpreted
   - Skills may not be loaded in time
   - Manual review is inconsistent

3. **Automated detection is feasible**
   - Pattern can be detected programmatically
   - False positive rate is acceptable
   - Feedback can be actionable

**Don't use defense-in-depth for:**

- Style preferences (one layer sufficient)
- Non-critical guidelines (agent instructions only)
- Patterns with high false positive rates (review fatigue)

## Measuring Layer Effectiveness

Track where violations are caught:

| Layer Caught | Interpretation                       |
| ------------ | ------------------------------------ |
| Layer 1      | Ideal - caught earliest, lowest cost |
| Layer 2      | Good - caught before PR submission   |
| Layer 3      | Acceptable - caught in PR review     |
| Production   | **Failure** - all layers failed      |

If Layer 3 consistently catches violations, it indicates:

- Layers 1-2 need improvement (better guidance, detection)
- The rule is unintuitive (consider simplifying)
- Layer 3 is working as designed (fail-safe)

## Related Patterns

### Workflow Gating Patterns

<!-- Source: docs/learned/ci/workflow-gating-patterns.md:18-60 -->

See [workflow-gating-patterns.md](../ci/workflow-gating-patterns.md) for multi-layer workflow control:

- Trigger filtering (GitHub events)
- Job conditions (runtime evaluation)
- Output-based skipping (dynamic gating)

Same principle: multiple independent layers providing flexible, safe control.

### Reliability Patterns

<!-- Source: docs/learned/planning/reliability-patterns.md:38-61 -->

See [reliability-patterns.md](../planning/reliability-patterns.md) for deterministic vs non-deterministic operations:

- Layer 1 (agent): Non-deterministic, high failure rate
- Layer 2 (staging): Fragile, can be undone
- Layer 3 (workflow): Deterministic, reliable

**Critical operations require Layer 3.** Layers 1-2 are defense-in-depth, not primary mechanisms.

## Implementation Checklist

When implementing defense-in-depth enforcement:

1. **Identify the critical rule** - What behavior must be prevented?
2. **Design Layer 3 first** - Automated PR check or CI validation
3. **Deploy Layer 3 immediately** - Don't wait for upstream layers
4. **Add upstream layers incrementally** - Agent guidance, skill rules
5. **Measure effectiveness** - Track where violations are caught
6. **Iterate on detection** - Reduce false positives, improve feedback

## Example: Three-Layer Enforcement in Practice

**Rule**: No verbatim code blocks >5 lines in `docs/learned/`

**Layer 1 (Agent)**: code-diff-analyzer agent warns during PR analysis

- **Catches**: ~30% of violations (when agent is invoked)
- **Cost**: Low (happens during normal workflow)
- **Feedback delay**: Immediate (during implementation)

**Layer 2 (Skill)**: learned-docs skill instructs to use source pointers

- **Catches**: ~50% of remaining violations (when skill loaded)
- **Cost**: Very low (passive guidance)
- **Feedback delay**: Immediate (during doc writing)

**Layer 3 (PR Review)**: learned-docs automated review posts inline comments

- **Catches**: 100% of violations that reach PR (deterministic detection)
- **Cost**: Low (automated, scales infinitely)
- **Feedback delay**: PR submission (minutes after push)

**Result**: Even if Layers 1-2 both fail (70% miss rate in this example), Layer 3 guarantees the rule is enforced before merge.

## Related Documentation

- [reliability-patterns.md](../planning/reliability-patterns.md) - Deterministic vs non-deterministic operations
- [workflow-gating-patterns.md](../ci/workflow-gating-patterns.md) - Multi-layer workflow control
- [stale-code-blocks-are-silent-bugs.md](../documentation/stale-code-blocks-are-silent-bugs.md) - Why verbatim code prevention matters
