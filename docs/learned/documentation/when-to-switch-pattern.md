---
title: Planless vs Planning Workflow Decision Framework
read_when:
  - "deciding whether to plan or start coding directly"
  - "realizing mid-task that the scope is larger than expected"
  - "choosing between erk wt create and plan mode"
tripwires:
  - action: "starting a multi-file change without entering plan mode"
    warning: "If the change touches 5+ files or has uncertain approach, plan first. See the decision matrix in when-to-switch-pattern.md."
  - action: "continuing to code after discovering scope is larger than expected"
    warning: "Stop and switch to planning. Mid-task warning signs (uncertainty accumulating, scope creeping, multiple valid approaches) indicate you should plan. See when-to-switch-pattern.md."
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# Planless vs Planning Workflow Decision Framework

Erk supports two workflows — planless (direct coding) and planning (plan-first). This document captures the cross-cutting decision framework for choosing between them and recognizing when to switch mid-task.

For the mechanics of each workflow, see the howto guides: [planless workflow](../../howto/planless-workflow.md) and [local workflow](../../howto/local-workflow.md).

For the mechanics of each workflow, see the planning workflow documentation in `docs/learned/planning/`.

## Why This Decision Matters

Choosing the wrong workflow has asymmetric costs:

- **Planning a trivial change** wastes minutes on overhead (issue creation, `.impl/` setup, progress tracking). Low cost.
- **Skipping planning on a complex change** leads to scope creep, missed edge cases, poor architectural decisions, and potentially hours of wasted implementation. High cost.

The decision framework below biases toward the lower-cost mistake: when in doubt, plan.

## Decision Matrix

| Factor                   | Planless                               | Planning                                    |
| ------------------------ | -------------------------------------- | ------------------------------------------- |
| **Files affected**       | 1-4                                    | 5+                                          |
| **Approach clarity**     | Obvious single solution                | Multiple valid approaches or uncertain      |
| **Research needed**      | None — you know exactly what to change | Codebase exploration required               |
| **Architectural impact** | Isolated to one component              | Cross-cutting across components             |
| **Describability**       | Entire change fits in 1-2 sentences    | Needs enumeration of steps or investigation |

**The one-sentence test:** If you can describe the entire change in one sentence and know exactly which files to touch, go planless. Otherwise, plan.

## Mid-Task Warning Signs

These signals indicate you should stop coding and switch to planning. They're ordered by how early they typically appear:

1. **Research needed** — "Let me grep for how this pattern is used elsewhere." If you need to understand existing code before proceeding, the task needs a plan.
2. **Uncertainty accumulating** — "Wait, how does this interact with that?" Each unanswered question compounds risk.
3. **Scope creeping** — "Oh, I also need to change these files." The task is bigger than the original mental model.
4. **Multiple valid approaches** — "Should I use approach A or B?" Architectural decisions deserve deliberation, not impulse.
5. **Refactoring urge** — "This would be cleaner if I restructured..." Refactoring during implementation conflates two concerns.

**The 30-minute check:** If you've been coding planless for 30 minutes and are still making decisions about approach (not just executing), switch to planning.

## How to Switch Mid-Task

**If you haven't committed yet:** Discard changes, enter plan mode, and start fresh. The research you did while coding informs the plan — it's not wasted.

**If you have committed work:** Keep what you have, enter plan mode, and plan the remaining work. The plan should reference your existing commits as context.

**Switching from planning to planless (rare):** If a plan reveals the task is simpler than expected, close the plan issue and make the change directly. This is uncommon — if you invested in planning, the implementation usually benefits from the plan's structure.

## Anti-Patterns

**Plan everything:** Planning a typo fix or variable rename wastes more time than the fix itself. The one-sentence test prevents this.

**Never plan:** "I'll figure it out as I go" is the most expensive anti-pattern. Large changes without plans lead to scope creep, rework, and poor architecture. If you catch yourself saying this about a non-trivial task, that's the strongest signal to plan.

**Switch too late:** Realizing deep into implementation that you should have planned means potentially discarding work. The 30-minute check and warning signs above catch this early.

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) — Understanding plan phases and state transitions
- [Planning Workflow](../planning/workflow.md) — `.impl/` folder structure and commands
