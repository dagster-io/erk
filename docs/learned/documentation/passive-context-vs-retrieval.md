---
read_when:
  - deciding whether to put knowledge in AGENTS.md, a skill, or a hook
  - diagnosing why an agent isn't using available documentation
  - adding a new tier of context injection
title: Passive Context vs. On-Demand Retrieval
tripwires:
  - action: never expect agents to self-diagnose knowledge gaps
    warning: use passive context or structural triggers
  - action: using this pattern
    warning:
      skills without explicit invocation triggers perform identically to having
      no documentation
---

# Passive Context vs. On-Demand Retrieval

_Based on: [AGENTS.md Outperforms Skills in Agent Evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) by Jude Gao, Vercel. Published January 27, 2026._

## The Retrieval Paradox

An agent cannot distinguish stale training data from correct knowledge. When a sync API becomes async, the agent confidently generates the old pattern. A skill exists that would correct it, but the agent never triggers it because _from its perspective, it already knows the answer_.

This is the retrieval paradox: **the agent needs knowledge to know it needs knowledge**. Any mechanism that relies on agent self-diagnosis of knowledge gaps inherits this fundamental limitation.

## Evidence: Vercel's Agent Evals

Vercel tested AI agents on Next.js 16 APIs absent from training data:

| Approach                                   | Pass Rate |
| ------------------------------------------ | --------- |
| No documentation (baseline)                | 53%       |
| Skills (default invocation)                | 53%       |
| Skills (explicit instructions to use them) | 79%       |
| Compressed docs index in AGENTS.md         | 100%      |

Skills with default invocation performed **identically to having no documentation at all** — in 56% of cases, the agent never invoked the skill. Adding explicit instructions improved to 79% but was brittle: different phrasings produced dramatically different outcomes, and the improvement didn't generalize across eval cases.

The compressed index eliminated the retrieval decision chain entirely (recognize gap → select skill → invoke → integrate), where each step has independent failure probability.

## Erk's Three-Tier Architecture

Erk applies these findings through three tiers of progressively more targeted context injection:

| Tier             | Mechanism                                          | When It Fires             | Purpose                                                         |
| ---------------- | -------------------------------------------------- | ------------------------- | --------------------------------------------------------------- |
| **Ambient**      | AGENTS.md with `@`-embedded index                  | Every turn                | Agent knows _what exists_ without deciding to look              |
| **Structural**   | UserPromptSubmit hooks, mandatory grep-before-plan | Start of each prompt      | Forces retrieval as a workflow step, not an agent judgment call |
| **Just-in-time** | PreToolUse hooks on Write/Edit                     | Moment of code generation | Fires at the exact point violations would occur                 |

<!-- Source: .claude/settings.json, hooks configuration -->

See the hooks configuration in `.claude/settings.json` for all three tiers' implementation.

### Why three tiers instead of one

Ambient context alone has a token budget — Vercel compressed 40KB to ~8KB to achieve 100%. The tiers solve this:

- **Tier 1** provides enough compressed awareness to prevent the retrieval paradox (the agent knows docs exist)
- **Tier 2** converts retrieval from an agent judgment ("should I search?") into a concrete workflow step ("grep before Plan"), reducing the decision chain from 4 steps to 2
- **Tier 3** catches violations that slip past the first two tiers by injecting rules at the exact moment they matter (e.g., Python coding standards injected only when editing `.py` files)

Each successive tier is more targeted but more expensive (consumes a hook invocation). The combination means no single tier needs to be comprehensive.

## Decision Framework: Where to Put Knowledge

| Knowledge characteristic                      | Place it in                    | Why                                                                        |
| --------------------------------------------- | ------------------------------ | -------------------------------------------------------------------------- |
| Agent needs it but doesn't know it needs it   | AGENTS.md (ambient)            | Retrieval paradox — agent won't search for what it thinks it already knows |
| Corrects training-data patterns               | AGENTS.md or PreToolUse hook   | Must be present _before_ the agent generates the wrong pattern             |
| User explicitly decides to invoke             | Skill                          | Human bypasses the retrieval paradox by making the decision                |
| Action-oriented workflow (not just knowledge) | Skill                          | Skills that _do things_ have natural invocation points                     |
| Too large for ambient context                 | docs/learned/ with index entry | Compressed index entry in AGENTS.md bridges to full content                |
| Rule at a specific code-editing moment        | PreToolUse hook                | Just-in-time injection at the exact moment of potential violation          |
| Dynamic state that changes during a session   | Skill or tool                  | Ambient context is static within a session                                 |

### Anti-patterns

**WRONG: Expecting agent to invoke a knowledge-only skill without a structural trigger.** This is the core Vercel finding — it performs identically to having no documentation.

**WRONG: Relying solely on prompt wording ("always check the style guide before editing Python").** Instruction sensitivity is brittle and doesn't generalize.

**CORRECT: Converting the conditional into a structural trigger.** Instead of "if writing Python, load dignified-python," use a PreToolUse hook on Write/Edit that detects `.py` files and injects the rules automatically.

## Key Insight: "Available" vs. "Used"

A skill that exists but isn't invoked provides zero value. Every documentation placement decision should be evaluated against _will the agent actually encounter this at the right moment_, not _could the agent find this if it tried_.
