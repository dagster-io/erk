---
title: Multi-Tier Agent Orchestration
read_when:
  - "designing agent workflows with parallel and sequential tiers"
  - "choosing between parallel and sequential agent execution"
  - "adding or modifying agents in the learn pipeline"
  - "deciding which model tier to assign an agent"
tripwires:
  - action: "running sequential analysis that could be parallelized"
    warning: "If agents analyze independent data sources, run them in parallel. Only use sequential execution when one agent's output is another's input."
  - action: "assigning opus to a mechanical extraction agent"
    warning: "Model escalation: haiku/sonnet for extraction and rule-based work, opus only for creative authoring. See the model escalation decision table."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Multi-Tier Agent Orchestration

The learn workflow's 2-tier orchestration pattern — parallel extraction feeding sequential synthesis — is the canonical example of multi-agent workflow design in erk. This document captures the cross-cutting design decisions and failure modes that apply whenever agents are composed into pipelines.

For the complete learn workflow (session discovery, preprocessing, issue creation), see [learn-workflow.md](learn-workflow.md). For file-based handoff safety patterns, see [agent-orchestration-safety.md](agent-orchestration-safety.md). For command-to-agent delegation decisions, see [agent-delegation.md](agent-delegation.md).

## Why Two Tiers?

The insight behind 2-tier orchestration is that analysis and synthesis have fundamentally different dependency structures.

**Analysis** reads from independent sources (PR diff, existing docs, session logs, PR comments). No analysis agent needs another's output. This means they can run concurrently — wall-clock time equals the slowest agent, not the sum.

**Synthesis** is inherently sequential: you can't identify documentation gaps without all the analysis results, you can't write a plan without the gap analysis, and you can't extract tripwires without the plan. Each step narrows and refines the previous step's output.

Merging these tiers into a single sequential pipeline would waste time during analysis. Merging them into a single parallel pipeline would produce incorrect synthesis (agents reading incomplete inputs). The 2-tier split is the minimum structure that captures both constraints.

## The Dependency Graph

<!-- Source: .claude/commands/erk/learn.md, "Agent Dependency Graph" section -->

The learn workflow's dependency graph has four parallel agents feeding a three-step sequential chain. See the "Agent Dependency Graph" section in `.claude/commands/erk/learn.md` for the canonical listing.

Key structural properties:

- **Parallel tier agents have no cross-dependencies** — each reads a different data source
- **Sequential tiers form a strict chain** — each agent's sole input is the previous agent's output file
- **The tier boundary is the synchronization point** — all parallel agents must complete before any sequential agent starts

## Model Escalation

Not all agents need the same model. The learn workflow demonstrates a deliberate model escalation pattern based on task type:

| Task Type                                                                                  | Model  | Rationale                                                                |
| ------------------------------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------ |
| Mechanical extraction (diff inventory, doc search, session mining, comment classification) | sonnet | Pattern matching and structured output; no creative judgment needed      |
| Rule-based synthesis (deduplication, classification, scoring)                              | sonnet | Applying explicit criteria to structured input; adversarial verification |
| Creative authoring (plan narrative, draft content starters)                                | opus   | Quality-critical prose that must be coherent and actionable              |
| Structured extraction (tripwire JSON from plan prose)                                      | sonnet | Pulling structured data from natural language; mechanical                |

<!-- Source: .claude/commands/erk/learn.md, model comments on each agent launch -->

The model choice is set by the orchestrating command, not by the agent definitions themselves. This means the same agent definition can be run at different model tiers in different contexts.

**Anti-pattern**: Using opus for all agents "to be safe." This wastes tokens and latency on mechanical work that sonnet handles identically. Reserve opus for agents whose output quality is the final deliverable.

## When to Use 2-Tier Orchestration

| Condition                                         | 2-Tier? | Why                                                                  |
| ------------------------------------------------- | ------- | -------------------------------------------------------------------- |
| Multiple independent data sources                 | Yes     | Parallel extraction saves wall-clock time                            |
| Final output requires combining all sources       | Yes     | Sequential synthesis ensures completeness                            |
| Analysis agents are expensive (10KB+ output each) | Yes     | Parallelism reduces total wait time significantly                    |
| Single data source, linear pipeline               | No      | No fan-out means no parallelism benefit                              |
| Fast analysis, expensive synthesis                | No      | The parallel tier saves negligible time                              |
| Each step's output is the next step's only input  | No      | This is just a sequential pipeline; tiers add unnecessary complexity |

## Anti-Patterns

| Pattern                                                                              | Why It Fails                                                                                                                                                                        |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Launching a synthesis agent before all parallel agents complete                      | Synthesis receives partial input, produces plausible-but-incomplete output. See [agent-orchestration-safety.md](agent-orchestration-safety.md) for the synchronization requirement. |
| Passing agent output inline instead of through scratch files                         | Bash tool truncates at ~10KB. Analysis agents routinely produce 10-30KB. Truncation is silent. See [agent-orchestration-safety.md](agent-orchestration-safety.md).                  |
| Adding a new parallel agent that secretly depends on another parallel agent's output | Breaks the independence invariant. If agent B needs agent A's output, agent B belongs in the sequential tier.                                                                       |
| Skipping the verification step between tiers                                         | Write tool can silently fail. A missing file means the synthesis agent wastes its entire context discovering the problem.                                                           |

## Adding a New Agent to the Learn Pipeline

When adding a new agent, the critical decisions are tier placement and model selection:

1. **Does it read from a primary data source (PR, session, docs)?** → Parallel tier
2. **Does it need another agent's output?** → Sequential tier, placed after its dependency
3. **Is its work mechanical (extraction, classification)?** → sonnet
4. **Does it produce prose that humans or implementing agents will read directly?** → opus

<!-- Source: .claude/agents/learn/ -->

Agent definitions live in `.claude/agents/learn/`. Each agent specifies its allowed tools in frontmatter, following the principle of least privilege — only the tools it actually needs.

The orchestrating command (`.claude/commands/erk/learn.md`) controls launch order, model selection, and file paths. Agent definitions are self-contained instructions that don't reference each other.

## Reuse Beyond Learn

The `/erk:replan` command uses the same 2-tier pattern: parallel analysis of multiple source plans, followed by sequential consolidation. The structural decisions (parallel extraction → file handoff → verification → sequential synthesis) transfer directly. The specific agents and models differ, but the orchestration shape is identical.

## Related Documentation

- [agent-orchestration-safety.md](agent-orchestration-safety.md) — File-based handoff, truncation failures, the three-step handoff pattern
- [agent-delegation.md](agent-delegation.md) — When to delegate to agents vs inline, multi-tier orchestration quick reference
- [learn-workflow.md](learn-workflow.md) — Complete learn workflow including session discovery, preprocessing, and issue creation
