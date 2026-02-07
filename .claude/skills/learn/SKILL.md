---
name: learn
description: >
  Extract insights from Claude Code sessions and create documentation plans. Use when running
  /erk:learn or /local:learn-plan-from-current-session. Provides anti-dismissal framing, pipeline
  overview, model assignments, and shared reference docs for the multi-agent learn pipeline.
---

# Learn Skill

Extract insights from Claude Code sessions and create documentation plans.

## Purpose

The verb "learn" means: analyze what happened, extract insights, and create an actionable plan to document those learnings.

**Audience**: All documentation produced by the learn pipeline is for AI agents, not human users. These docs are "token caches" — preserved reasoning and research so future agents don't have to recompute it.

## Anti-Dismissal Framing

**Document reality**: Capture the world as it is, not as we wish it to be. "This is non-ideal but here's the current state" is valuable documentation. Tech debt, workarounds, quirks — document them.

**Bias toward capturing**: When uncertain whether something is worth documenting, include it. Over-documentation is better than losing insights.

**Reject dismissiveness**: If you find yourself thinking "this doesn't need documentation," pause. That instinct is often wrong. New features, patterns, and capabilities almost always benefit from documentation, even when the code is "clear."

**"Self-documenting code" is NOT a valid skip reason**: Code shows WHAT, not WHY. Context, relationships, and gotchas need documentation.

## Pipeline Overview

The learn pipeline uses a multi-agent architecture with file-based composition:

```
Parallel Tier (can run simultaneously):
  ├─ SessionAnalyzer (per session XML)          — haiku
  ├─ CodeDiffAnalyzer (if PR exists)            — haiku
  ├─ ExistingDocsChecker                        — sonnet
  └─ PRCommentAnalyzer (if PR exists)           — haiku

Sequential Tier 1 (depends on Parallel Tier):
  └─ DocumentationGapIdentifier                 — sonnet

Sequential Tier 2 (depends on Sequential Tier 1):
  └─ PlanSynthesizer                            — opus

Sequential Tier 3 (depends on Sequential Tier 2):
  └─ TripwireExtractor                          — haiku
```

## Model Assignments

| Agent                      | Model  | Rationale                                                                 |
| -------------------------- | ------ | ------------------------------------------------------------------------- |
| SessionAnalyzer            | haiku  | Mechanical extraction from XML; deterministic pattern matching            |
| CodeDiffAnalyzer           | haiku  | Structured inventory of changes; no creative reasoning needed             |
| ExistingDocsChecker        | sonnet | Search and classification; upgraded from haiku to reduce dismissiveness   |
| PRCommentAnalyzer          | haiku  | Mechanical classification of comments; deterministic                      |
| DocumentationGapIdentifier | sonnet | Deduplication and synthesis; upgraded from haiku to reduce dismissiveness |
| PlanSynthesizer            | opus   | Creative authoring of narrative context; quality-critical output          |
| TripwireExtractor          | haiku  | Mechanical extraction of structured data from prose                       |

## Shared Pipeline Steps

The learn pipeline is shared by two commands:

1. **`/erk:learn`** — Plan-associated learning (requires issue, PR, sessions)
2. **`/local:learn-plan-from-current-session`** — Current-session learning (no issue/PR required)

Both commands use the same reference docs for the shared pipeline steps:

| Step            | Reference Doc                          | Description                                         |
| --------------- | -------------------------------------- | --------------------------------------------------- |
| Launch agents   | `references/launch-analysis-agents.md` | Parallel agent launch blocks                        |
| Collect results | `references/collect-results.md`        | TaskOutput collection, Write to scratch             |
| Synthesize      | `references/synthesis-pipeline.md`     | GapIdentifier → PlanSynthesizer → TripwireExtractor |
| Review plan     | `references/review-plan.md`            | Validation checkpoint, outdated doc check           |
| Save plan       | `references/save-learn-plan.md`        | Validate, save to issue, store tripwires            |

## Agent Definitions

Agent instructions live in `.claude/agents/learn/`:

- `session-analyzer.md` — Extract patterns from preprocessed session XML
- `code-diff-analyzer.md` — Inventory PR changes
- `existing-docs-checker.md` — Search for duplicates and contradictions
- `documentation-gap-identifier.md` — Synthesize and deduplicate candidates
- `plan-synthesizer.md` — Create narrative context and draft content
- `tripwire-extractor.md` — Extract structured tripwire data

## Scratch Storage Layout

All intermediate files go to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/`:

```
learn/                          # Preprocessed session XML files
learn-agents/                   # Agent outputs
  ├── session-<id>.md           # SessionAnalyzer outputs
  ├── self-reflection.md        # Self-reflection output (current-session only)
  ├── diff-analysis.md          # CodeDiffAnalyzer output
  ├── existing-docs-check.md    # ExistingDocsChecker output
  ├── pr-comments-analysis.md   # PRCommentAnalyzer output
  ├── gap-analysis.md           # DocumentationGapIdentifier output
  ├── learn-plan.md             # PlanSynthesizer output
  └── tripwire-candidates.json  # TripwireExtractor output
```
