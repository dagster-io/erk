---
title: Token Optimization Patterns
read_when:
  - designing multi-agent workflows that process multiple documents
  - experiencing context bloat from fetching large payloads into parent agent
  - choosing where to place content fetching in an orchestration pipeline
  - deciding which model tier to use for delegated work
tripwires:
  - action: "fetching N large documents into parent agent context"
    warning: "Delegate content fetching to child agents. Parent receives only analysis summaries, not raw content. Achieves O(1) parent context instead of O(n). See token-optimization-patterns.md."
  - action: "using opus/sonnet for mechanical data fetching or formatting tasks"
    warning: "Use haiku for mechanical work (fetch, parse, format). Reserve expensive models for synthesis and reasoning."
---

# Token Optimization Patterns

When orchestrating agents that each process large documents, naive approaches cause O(n) token bloat in the parent context. This document captures two delegation patterns — and the decision framework for choosing between them — that keep parent context usage constant regardless of input count.

## Core Insight: Content Fetching Is the Token Sink

The parent agent's context is the bottleneck. Every token fetched into parent context persists for the entire conversation. The optimization is always the same: move fetching into child agents so the parent only sees summaries.

## Pattern 1: Parallel Delegation for N-Document Analysis

**When**: Multiple large documents need independent analysis before synthesis (plan consolidation, multi-PR release notes, cross-worktree session aggregation).

**How it works**:

1. Parent validates metadata only (labels, state, issue numbers) — never fetches document bodies
2. Parent launches N child agents **in parallel** (`run_in_background: true`), each responsible for fetching and analyzing its own document
3. Each child returns a compact analysis summary
4. Parent synthesizes from summaries only

**Why this matters**: For N=7 plans at ~5000 tokens each, the naive approach puts ~35,000 tokens in parent context. With delegation, parent context grows by N × summary_size (typically ~8,000 total) — an 82% reduction observed in practice.

<!-- Source: .claude/commands/erk/replan.md, Steps 3-4 -->

The `/erk:replan` command demonstrates this pattern. Step 3 explicitly skips content fetching ("Plan content is fetched by each Explore agent in Step 4, not in the main context"), and Step 4 launches parallel Explore agents that each fetch their own plan issue as their first action.

<!-- Source: .claude/commands/local/replan-learn-plans.md, Step 3 -->

The `/local:replan-learn-plans` command builds on this by querying all open learn plans and passing the full set to `/erk:replan` for parallel investigation.

### Critical: Wait for All Background Agents

A subtle failure mode: creating the consolidated output before all background agents complete. The parent **must** use `TaskOutput` with `block: true` and adequate timeout before proceeding to synthesis. Incomplete investigation data produces incomplete plans.

## Pattern 2: Single-Agent Delegation for Mechanical Work

**When**: A single multi-step fetch-parse-format pipeline can be fully delegated to one cheap agent.

**How it works**:

1. Parent crafts a structured prompt specifying exact output format
2. Parent launches a single Task agent with `model: "haiku"` (mechanical work doesn't need expensive models)
3. Child fetches, parses, and formats data
4. Parent consumes structured result directly

<!-- Source: .claude/commands/erk/objective-next-plan.md, Step 2 -->

The `/erk:objective-next-plan` command demonstrates this. Step 2 delegates objective data fetching (issue metadata, roadmap parsing, status mapping, step recommendation) to a haiku-tier general-purpose agent. The parent never makes the 3+ sequential fetches itself — it receives a single structured summary.

<!-- Source: docs/learned/reference/objective-summary-format.md -->

The output contract is specified in `objective-summary-format.md`, which defines the exact sections (OBJECTIVE, STATUS, ROADMAP, PENDING_STEPS, RECOMMENDED) the Task agent must return.

## Decision Framework: Which Pattern to Use

| Condition | Pattern | Why |
| --- | --- | --- |
| N documents, each analyzed independently | Parallel delegation | Parallelism + O(1) parent context |
| Single multi-step fetch-parse pipeline | Single-agent delegation | Reduces parent turns and token waste |
| Documents are small (<500 tokens each) | Fetch in parent | Delegation overhead exceeds savings |
| Parent needs full content for synthesis | Fetch in parent | Summaries lose necessary detail |
| Sequential dependencies between documents | Sequential delegation | Can't parallelize, but still avoid parent bloat |
| Child agents need to communicate | Rethink architecture | Agent-to-agent communication isn't supported |

## Model Selection for Delegated Work

| Work type | Model | Rationale |
| --- | --- | --- |
| Fetch, parse, format (mechanical) | haiku | Sufficient capability, lowest cost |
| Codebase investigation, analysis | Default (sonnet) | Needs reasoning for status assessment |
| Plan synthesis, creative decisions | Parent agent | Highest-quality reasoning required |

**Anti-pattern**: Using opus or sonnet for data fetching and formatting. The `/erk:objective-next-plan` command explicitly uses haiku for this reason — the work is mechanical and doesn't benefit from more capable models.

## Anti-Patterns

**Fetching "just to inspect"**: Parent fetches a document to decide whether it needs analysis, then delegates the analysis. The inspection itself wastes tokens — delegate the fetch-and-decide as a unit.

**Summarizing summaries**: Launching a child agent to summarize another child agent's summary. If the first summary is too large, fix the first agent's output contract, don't add layers.

**Skipping the output contract**: Delegating without specifying the return format. The child agent returns verbose, unstructured output that consumes as many parent tokens as the raw content would have.

## Related Documentation

- [Objective Summary Format](../reference/objective-summary-format.md) — structured output specification for delegated objective fetching
- [Agent Orchestration Safety Patterns](agent-orchestration-safety.md) — file-based agent output pattern for large results
