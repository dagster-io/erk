---
title: Model Selection for Learn Workflow Agents
read_when:
  - "implementing multi-agent workflows with Task tool"
  - "optimizing cost/quality tradeoffs in agent orchestration"
  - "adding or modifying learn workflow agents"
  - "understanding tier-based model selection"
tripwires:
  - action: "modifying learn command to add/remove/reorder Task invocations"
    warning: "Before applying model parameters, verify tier structure (parallel vs sequential). Misplacing haiku task in final synthesis tier degrades quality. Pattern: parallel extraction uses haiku, sequential synthesis uses opus."
  - action: "adding new agents to learn workflow"
    warning: "Document input/output format clearly and test file passing integration. Architecture assumes stateless agents with file-based composition."
---

# Model Selection for Learn Workflow Agents

The learn workflow uses tier-based model selection to optimize cost while preserving quality. This pattern applies broadly to any multi-agent workflow where different agents have different cognitive requirements.

## Overview

| Tier                 | Agents                                                 | Model | Rationale                                               |
| -------------------- | ------------------------------------------------------ | ----- | ------------------------------------------------------- |
| Parallel extraction  | SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker | Haiku | Pattern matching, structured extraction, classification |
| Sequential synthesis | DocumentationGapIdentifier                             | Haiku | Rule-based deduplication and prioritization             |
| Final synthesis      | PlanSynthesizer                                        | Opus  | Creative authoring, narrative generation, draft content |

## Pattern: Extract Cheap, Synthesize Premium

When building multi-agent workflows:

- **Extraction/classification tasks** - Haiku (fast, cheap, deterministic)
- **Analysis with explicit rules** - Haiku or Sonnet
- **Creative synthesis/authoring** - Opus (quality-critical)

The key insight: extraction tasks produce similar quality regardless of model, but synthesis tasks benefit significantly from higher-capability models.

## When to Apply This Pattern

Use tier-based model selection when:

1. **Workflow has multiple agents with different cognitive requirements** - Some do mechanical extraction while others require reasoning
2. **Cost optimization matters** - Parallel tier runs multiple instances simultaneously
3. **Quality of final output is critical** - Premium model on synthesis preserves quality where it matters most

## Cost Implications

Haiku for parallel tier provides significant savings because:

- Multiple agents run simultaneously (e.g., one SessionAnalyzer per session file)
- Extraction tasks produce similar quality regardless of model
- Speed improvements compound across parallel execution
- Haiku's lower latency improves overall workflow time

## Model Selection Guidelines

| Task Type                       | Recommended Model | Examples                                   |
| ------------------------------- | ----------------- | ------------------------------------------ |
| Structured extraction           | Haiku             | Parsing XML, extracting patterns from logs |
| Classification/categorization   | Haiku             | Labeling items, sorting into buckets       |
| Rule-based transformation       | Haiku             | Deduplication, filtering, prioritization   |
| Complex analysis with reasoning | Sonnet            | Code review, architectural decisions       |
| Creative writing/narrative      | Opus              | Documentation drafts, explanatory content  |
| Novel problem solving           | Opus              | Design decisions, trade-off analysis       |

## Related Topics

- [Learn Workflow](learn-workflow.md) - Full learn workflow documentation
- [Task Tool Parameter Reference](../commands/task-parameter-reference.md) - How to specify model in Task invocations
