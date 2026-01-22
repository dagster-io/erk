# Documentation Plan: Add Model Selection to Learn Workflow Agents

## Context

This implementation added explicit model selection to the `erk learn` workflow, routing each of the 5 subagents to the appropriate Claude model based on task complexity. The core insight is a **tier-based cost optimization pattern**: analysis/extraction tasks (SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker, DocumentationGapIdentifier) use Haiku for speed and cost savings, while the final synthesis task (PlanSynthesizer) uses Opus for higher-quality reasoning output.

The implementation was straightforward—adding `model` parameters to 5 existing Task invocations in `.claude/commands/erk/learn.md`—but the underlying pattern is valuable for future multi-agent workflows. The key documentation gap is that the **reusable principle** (extract cheap, synthesize premium) and the **Task tool model parameter capability** are not yet documented anywhere, making it hard for future implementations to discover and apply this pattern.

Future agents implementing multi-step workflows should understand: (1) when to use tier-based model selection, (2) how to specify the model parameter in Task invocations, and (3) the trade-offs between speed/cost and reasoning quality at each tier boundary.

## Raw Materials

https://gist.github.com/schrockn/969e2eab5aa8a8f106bfe11bcebfcfcb

## Summary

| Metric                    | Count |
| ------------------------- | ----- |
| Documentation items       | 4     |
| Contradictions to resolve | 0     |
| Tripwires to add          | 3     |

## Documentation Items

### 1. Model Selection Strategy for Learn Agents [HIGH] - CREATE

**Location:** `docs/learned/planning/model-selection-learn-workflow.md`

**Source:** [Plan] + [Impl]

**Draft content starter:**

```markdown
---
title: Model Selection for Learn Workflow Agents
read_when:
  - "Implementing multi-agent workflows with Task tool"
  - "Optimizing cost/quality tradeoffs in agent orchestration"
  - "Adding or modifying learn workflow agents"
---

# Model Selection for Learn Workflow Agents

## Overview

The learn workflow uses tier-based model selection to optimize cost while preserving quality:

| Tier | Agents | Model | Rationale |
|------|--------|-------|-----------|
| Parallel extraction | SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker | Haiku | Pattern matching, structured extraction, classification tasks |
| Sequential synthesis 1 | DocumentationGapIdentifier | Haiku | Rule-based deduplication and prioritization |
| Sequential synthesis 2 | PlanSynthesizer | Opus | Creative authoring, narrative generation, draft content |

## Pattern: Extract Cheap, Synthesize Premium

When building multi-agent workflows:
- **Extraction/classification tasks** → Haiku (fast, cheap, deterministic)
- **Analysis with explicit rules** → Haiku or Sonnet
- **Creative synthesis/authoring** → Opus (quality-critical)

## When to Apply This Pattern

Use tier-based model selection when:
1. Workflow has multiple agents with different cognitive requirements
2. Some agents do mechanical extraction while others require reasoning
3. Cost optimization matters (parallel tier runs multiple instances)

## Cost Implications

Haiku for parallel tier provides significant savings because:
- Multiple agents run simultaneously (one SessionAnalyzer per session file)
- Extraction tasks produce similar quality regardless of model
- Speed improvements compound across parallel execution
```

---

### 2. Task Tool Model Parameter Reference [HIGH] - CREATE

**Location:** `docs/learned/commands/task-parameter-reference.md`

**Source:** [Plan] + [Impl]

**Draft content starter:**

```markdown
---
title: Task Tool Parameter Reference
read_when:
  - "Spawning subagents with Task tool"
  - "Specifying model for Task invocations"
  - "Understanding Task tool capabilities"
---

# Task Tool Parameter Reference

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

| Model | Cost | Speed | Use For |
|-------|------|-------|---------|
| haiku | Low | Fast | Orchestration, extraction, classification, iterative execution |
| sonnet | Medium | Medium | Complex analysis, code review, decision-making |
| opus | High | Slower | Complex reasoning, novel problem solving, multi-step planning |

### Best Practices

1. **Always specify explicitly** - Don't rely on defaults; model selection affects cost and quality
2. **Match to task complexity** - Use haiku for mechanical tasks, opus for synthesis
3. **Consider parallel execution** - Haiku saves significantly when multiple agents run simultaneously
```

---

### 3. Learn Workflow Tier Architecture [MEDIUM] - UPDATE

**Location:** `docs/learned/planning/learn-workflow.md`

**Source:** [Plan]

**Action:** Add section documenting the 3-tier structure with model assignments:

```markdown
## Agent Tier Architecture

The learn workflow orchestrates 5 agents across 3 tiers:

### Parallel Tier (Haiku)
Runs simultaneously via `run_in_background: true`:
- **SessionAnalyzer** - Extracts patterns from preprocessed session XML
- **CodeDiffAnalyzer** - Inventories PR changes
- **ExistingDocsChecker** - Searches for duplicates/contradictions

### Sequential Tier 1 (Haiku)
Depends on parallel tier outputs:
- **DocumentationGapIdentifier** - Synthesizes and deduplicates candidates

### Sequential Tier 2 (Opus)
Depends on Sequential Tier 1:
- **PlanSynthesizer** - Creates narrative context and draft content

### Tier Boundaries

Agents within the same tier can run in parallel. Tier boundaries enforce sequential ordering:
- Parallel tier must complete before Sequential Tier 1 starts
- Sequential Tier 1 must complete before Sequential Tier 2 starts
```

---

### 4. Inline Model Rationale in learn.md [MEDIUM] - UPDATE

**Location:** `.claude/commands/erk/learn.md`

**Source:** [PR #5585]

**Action:** Add comments explaining why each agent uses its assigned model. Example:

```markdown
# Session analysis uses haiku - mechanical pattern extraction from XML
Task(
  subagent_type: "general-purpose",
  model: "haiku",  # Extraction task - haiku is fast and sufficient
  ...
)

# Plan synthesis uses opus - creative authoring requires quality reasoning
Task(
  subagent_type: "general-purpose",
  model: "opus",  # Synthesis task - opus produces higher-quality drafts
  ...
)
```

---

## Tripwire Additions

Add to `docs/learned/tripwires.md`:

### 1. Task Invocation Model Parameter

```yaml
tripwires:
  - action: "Adding new Task invocation to any command file"
    warning: "Always include explicit `model` parameter (haiku/opus/sonnet); don't rely on defaults. Model selection affects cost and quality."
```

### 2. Learn Command Tier Structure

```yaml
tripwires:
  - action: "Modifying learn command to add/remove/reorder Task invocations"
    warning: "Before applying model parameters, verify tier structure (parallel vs sequential). Misplacing haiku task in final synthesis tier degrades quality. Reference: parallel tasks use haiku, sequential tier 1 uses haiku, sequential tier 2 uses opus."
```

### 3. Learn Workflow Agent Composition

```yaml
tripwires:
  - action: "Adding new agents to learn workflow"
    warning: "Document input/output format clearly and test file passing integration. Architecture assumes stateless agents with file-based composition."
```

---

## Skip Justifications

| Item | Reason |
|------|--------|
| Immutable plan pattern | Internal implementation detail; already implicit in planning workflow design |
| Agent-specific model assignments | Configuration values live in learn.md; pattern doc covers rationale |

## Verification

After implementation:
1. Run `erk docs sync` to regenerate tripwires.md
2. Verify new docs appear in `docs/learned/index.md`
3. Search for "model selection" in docs to confirm discoverability