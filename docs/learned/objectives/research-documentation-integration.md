---
title: Documentation Capture from Objective Work
read_when:
  - "deciding whether objective work should produce learned docs"
  - "choosing between manual doc capture and the learn workflow during an objective"
  - "capturing cross-cutting discoveries from multi-plan investigations"
tripwires:
  - action: "creating documentation for a pattern discovered during an objective before the pattern is proven in a merged PR"
    warning: "Only document patterns proven in practice. Speculative patterns from in-progress objectives go stale. Wait until the PR lands and the pattern is validated."
  - action: "creating a learned doc that rephrases an objective's action comment lessons"
    warning: "Objectives already capture lessons in action comments. Only create a learned doc when the insight is reusable beyond this specific objective."
last_audited: "2026-02-08"
audit_result: edited
---

# Documentation Capture from Objective Work

Objectives span multiple plans and sessions, accumulating cross-cutting knowledge that no single plan captures. This document explains when that knowledge should become learned documentation and how to choose between the two capture paths.

## The Core Question: Document or Not?

Not every objective produces documentation. The test is whether the objective revealed **reusable cross-cutting knowledge** — insights spanning multiple code locations that would help future agents on unrelated tasks.

| Discovery type                                     | Document? | Why                                                              |
| -------------------------------------------------- | --------- | ---------------------------------------------------------------- |
| Architectural pattern spanning multiple files      | Yes       | Cross-cutting insight that can't live in any single code comment |
| Tripwire from a mistake that cost significant time | Yes       | Prevents future agents from repeating the lesson                 |
| Integration pattern between two systems            | Yes       | Connects knowledge agents can't derive from reading one file     |
| Bug fix specific to this objective                 | No        | Single-artifact knowledge — belongs in a code comment            |
| Temporary workaround planned for removal           | No        | Will go stale the moment the workaround is removed               |
| Pattern not yet proven in a merged PR              | No        | Speculative — wait until the implementation lands                |
| Knowledge already covered by existing docs         | No        | Duplication creates contradictions when one copy drifts          |

## Two Capture Paths

Objective documentation enters the system through two distinct paths. Choosing the wrong one wastes effort.

### Path 1: Manual Capture During Work

Create learned docs directly when you discover knowledge that's **immediately useful to other agents** regardless of whether this objective's PR has merged. This is the right path for tripwires, decision rationale, and architectural patterns you've already validated.

Record what was documented in the objective's action comment, creating a bidirectional trail: the objective references the doc it produced, and the doc's context references the objective that prompted the discovery. See the action comment format in the objective skill (`objective/SKILL.md`).

### Path 2: Automated Extraction via Learn Workflow

After an objective's plan produces a merged PR, `/erk:learn` extracts documentation candidates from session logs. This is the right path for insights you didn't realize were worth documenting, or for extracting patterns from implementation sessions focused on shipping code.

The learn workflow creates a separate plan issue for documentation that goes through human review before implementation — insights are captured but not committed without review. See [Learn Workflow](../planning/learn-workflow.md) for the full pipeline.

### Choosing Between Paths

| Situation                                        | Path           | Reasoning                                                                  |
| ------------------------------------------------ | -------------- | -------------------------------------------------------------------------- |
| You hit a painful tripwire mid-objective         | Manual         | Capture immediately so parallel sessions benefit                           |
| You discovered a subtle integration pattern      | Manual         | Cross-cutting patterns need deliberate authoring, not automated extraction |
| PR just merged, want to capture session insights | Learn workflow | Automated extraction catches things you missed during implementation       |
| Objective complete, want comprehensive review    | Learn workflow | Multi-agent analysis pipeline finds gaps better than manual review         |

## Anti-Patterns

**Documenting before proving**: Creating learned docs for patterns still in an in-progress objective phase. The pattern may change before the PR merges, leaving a stale doc. Wait until the PR lands.

**Duplicating the action log**: Objectives already capture lessons learned in action comments. Don't create a learned doc that just rephrases what's in the objective issue. Only create a doc when the insight is **reusable beyond this objective**.

**Skipping the learn workflow**: After landing a PR from objective work, running `/erk:learn` on the parent plan often surfaces documentation candidates that weren't obvious during implementation. The automated extraction is cheap and catches blind spots.

## Related Documentation

- [Learn Workflow](../planning/learn-workflow.md) — Automated documentation extraction pipeline
- [Objective Skill](../../../.claude/skills/objective/SKILL.md) — Action comment format and objective structure
