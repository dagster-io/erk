---
title: Model Selection for Learn Workflow Agents
read_when:
  - "implementing multi-agent workflows with Task tool"
  - "optimizing cost/quality tradeoffs in agent orchestration"
  - "adding or modifying learn workflow agents"
tripwires:
  - action: "Adding new Task invocation to any command file"
    warning: "Always include explicit `model` parameter (haiku/sonnet/opus); don't rely on defaults. Model selection affects cost and quality."
---

# Model Selection for Learn Workflow Agents

The learn workflow uses tier-based model selection to optimize cost while preserving quality. This document explains the pattern and when to apply it.

## Overview

The learn workflow orchestrates 5 agents across 3 tiers, each assigned to an appropriate model based on task complexity:

| Tier                   | Agents                                                 | Model | Rationale                                   |
| ---------------------- | ------------------------------------------------------ | ----- | ------------------------------------------- |
| Parallel extraction    | SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker | Haiku | Pattern matching, structured extraction     |
| Sequential synthesis 1 | DocumentationGapIdentifier                             | Haiku | Rule-based deduplication and prioritization |
| Sequential synthesis 2 | PlanSynthesizer                                        | Opus  | Creative authoring, narrative generation    |

## Pattern: Extract Cheap, Synthesize Premium

When building multi-agent workflows:

- **Extraction/classification tasks** → Haiku (fast, cheap, deterministic)
- **Analysis with explicit rules** → Haiku or Sonnet
- **Creative synthesis/authoring** → Opus (quality-critical)

The key insight: extraction tasks produce similar quality regardless of model. Save expensive models for tasks that require creative reasoning or nuanced judgment.

## When to Apply This Pattern

Use tier-based model selection when:

1. **Multiple agents with different cognitive requirements** - Some do mechanical extraction while others require reasoning
2. **Parallel execution matters** - Cost savings compound when multiple agents run simultaneously
3. **Final output quality is critical** - Use premium model only for the user-facing synthesis step

## Cost Implications

Haiku for the parallel tier provides significant savings because:

- Multiple agents run simultaneously (e.g., one SessionAnalyzer per session file)
- Extraction tasks produce similar quality regardless of model
- Speed improvements compound across parallel execution

## Agent Tier Architecture

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

## Related Topics

- [Task Tool Parameter Reference](../commands/task-parameter-reference.md) - How to specify model in Task invocations
- [Learn Workflow](learn-workflow.md) - Full learn workflow documentation
