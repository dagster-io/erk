---
title: "Passive Context vs. On-Demand Retrieval"
read_when:
  - "deciding whether to put knowledge in AGENTS.md or a skill"
  - "structuring documentation for agent consumption"
  - "designing how agents discover and use project knowledge"
  - "evaluating why an agent isn't using available documentation"
---

# Passive Context vs. On-Demand Retrieval

_Based on: [AGENTS.md Outperforms Skills in Agent Evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) by Jude Gao, Vercel. Published January 27, 2026. Document authored January 29, 2026._

Vercel's agent evals found that documentation embedded in AGENTS.md dramatically outperforms skills that agents must decide to invoke. This has direct implications for how we structure agent-facing documentation.

## The Core Evidence

Vercel tested AI agents on Next.js 16 APIs absent from training data:

| Approach                                   | Pass Rate |
| ------------------------------------------ | --------- |
| No documentation (baseline)                | 53%       |
| Skills (default invocation)                | 53%       |
| Skills (explicit instructions to use them) | 79%       |
| Compressed docs index in AGENTS.md         | 100%      |

Skills with default invocation performed **identically to having no documentation at all**. In 56% of eval cases, the agent never invoked the skill.

Source: [Vercel Blog — AGENTS.md Outperforms Skills in Agent Evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)

## Why Agents Fail to Self-Diagnose Knowledge Gaps

The fundamental problem: **an agent cannot distinguish stale training data from correct knowledge**. When a sync API becomes async, the agent confidently generates the old pattern. A skill exists that would correct it, but the agent never triggers it because from its perspective, it already knows the answer.

This is the retrieval paradox: the agent needs knowledge to know it needs knowledge. Lookup mechanisms assume the agent can identify its own blind spots, which is precisely what blind spots prevent.

## Why Passive Context Works

AGENTS.md eliminates the decision chain entirely. Instead of:

1. Recognize knowledge gap
2. Select correct skill
3. Invoke skill
4. Integrate skill output

The documentation is simply present on every turn. The agent reads it before generating code, not after generating wrong code and (maybe) realizing something is off.

Each step in the retrieval chain has a non-trivial failure probability. If each succeeds 90% of the time, a 4-step chain succeeds only 66% of the time. Removing the chain entirely is why the improvement is so dramatic.

## The Two-Tier Architecture

Raw documentation was ~40KB. The compressed index that achieved 100% was ~8KB (80% reduction). The viable pattern is:

- **Tier 1 (ambient)**: Compressed navigable index in AGENTS.md — enough to know _what exists and where to find it_
- **Tier 2 (on-demand)**: Full documentation on disk, accessed via targeted reads when the index signals relevance

The index doesn't contain all the knowledge. It provides enough context for the agent to _know what it doesn't know_ — which is exactly what skills fail to provide.

## When Each Approach Wins

### Passive context (AGENTS.md / routing files)

- Static knowledge the agent needs but doesn't know it needs
- Corrective information for patterns that differ from training data
- Navigation indexes that enable targeted lookups
- Critical rules that apply universally

### On-demand retrieval (skills)

- **User-triggered workflows** where the human decides to invoke (e.g., `/migrate-to-v16`)
- Action-oriented skills that _do things_, not just provide knowledge
- Knowledge that exceeds what fits in passive context even after compression
- Dynamic state that changes during a session

The key distinction: explicit user invocation (`/migrate`) avoids the "agent doesn't realize it needs this" failure. The problematic pattern is expecting the agent to decide when to invoke a skill for knowledge it doesn't know it lacks.

## Instruction Sensitivity Is Fragile

Adding explicit instructions to use skills improved pass rates from 53% to 79%, but this was brittle:

- Different phrasings of the same instruction produced dramatically different outcomes
- An agent would correctly apply knowledge in one file but miss required changes in another file in the same task
- The improvement didn't generalize across eval cases

You cannot engineer reliability through prompt wording when the mechanism depends on agent judgment about when to invoke tools.

## Implications for Documentation Design

### Minimize agent decision points

Every conditional ("if the agent encounters X, it should do Y") is a branch that can fail. Where possible, make knowledge ambient rather than conditional.

### Compress aggressively for ambient context

A navigable index outperforms full docs that require active retrieval. Structure documentation so the compressed form is useful on its own and points to detail when needed.

### Framework authors: ship agent-consumable artifacts

Documentation now has two audiences — humans and agents — with different consumption patterns. Agents need compression, ambient availability, and structured indexes. These may require different artifacts from the same source material.

### Don't conflate "available" with "used"

A skill that exists but isn't invoked provides zero value. Measure whether agents actually use documentation, not just whether it's theoretically accessible.

## Relationship to Erk's Architecture

Erk's AGENTS.md already implements a routing-file pattern aligned with these findings:

- **Routing table**: Compressed index pointing to skills and docs (ambient tier)
- **Skills**: Loaded on-demand but triggered by routing rules, not agent self-diagnosis
- **docs/learned/**: Full documentation available for targeted reads (on-demand tier)

The Vercel findings validate this architecture. The routing table in AGENTS.md serves the same role as Vercel's compressed docs index — it gives the agent enough ambient awareness to know where to look, rather than requiring the agent to independently realize it needs to look.

Areas where these findings suggest refinement:

- **Tripwires as ambient context**: Tripwire rules in AGENTS.md act as passive triggers rather than relying on agent self-diagnosis. This aligns with the passive-context advantage.
- **Skill loading hooks**: Erk's hook system that reminds agents to load skills bridges the gap — it's a passive mechanism that triggers active loading, combining both approaches.
- **Just-in-time PreToolUse hooks**: The `dignified-python-pre-edit.sh` PreToolUse hook injects core rules immediately before editing `.py` files. This converts the fragile conditional "if you're writing Python, load dignified-python" into an automatic observable trigger (file extension detection). This is a third tier: ambient context (AGENTS.md) provides the rules, per-prompt hooks (UserPromptSubmit) remind that they exist, and just-in-time hooks (PreToolUse) fire at the exact moment violations would occur.
- **Index compression**: The docs/learned/index.md could be further compressed for inclusion as ambient context rather than requiring a separate read step.
- **Mandatory grep-before-plan**: AGENTS.md now instructs agents to grep `docs/learned/` before launching Plan agents. This is a structural application of the two-tier architecture — the ambient index tells the agent _what exists_, and the mandatory grep ensures the agent actually retrieves relevant docs before planning. By making retrieval a concrete workflow step ("grep before Plan") rather than a passive suggestion ("scan the index"), we reduce the decision chain from "notice gap → decide to search → search → integrate" to just "search → integrate."
