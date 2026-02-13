# Plan: Objective Body Lifecycle Redesign

## Context

Objective bodies are living documents that span weeks of work across multiple PRs. Today, the only body mutations after creation are mechanical (roadmap step status/PR via `update-roadmap-step`) and a now-deprecated "Current Focus" section. The prose sections (Goal, Design Decisions, Implementation Context) are write-once at creation time and never reconciled against reality.

This is a problem because:
- **Discovery**: Implementation reveals things the creator didn't anticipate. Design decisions get overridden, architecture descriptions become wrong, step scopes change.
- **Drift**: The codebase changes from other work between objective sessions. Implementation context becomes stale.
- **Silent staleness**: No agent ever reports "this objective says X but the code now does Y."

The user's core requirement: **"I always want agents to report back what has changed that contradicts what the text of the objective says and update it."**

## Part 1: Section Taxonomy

Every section in the objective body should have a clear **owner** (who updates it) and **lifecycle** (when it's updated).

### Proposed taxonomy:

| Section | Owner | Created | Updated When | How |
|---------|-------|---------|-------------|-----|
| **Goal** | Human at creation | Creation | Rarely (pivot only) | Manual or LLM reconciliation |
| **Design Decisions** | Agent | Creation | After PR overrides one | LLM reconciliation at landing |
| **Roadmap tables** | Exec commands | Creation | Plan assigned / PR landed | `update-roadmap-step`, `objective-mark-landed` |
| **Step descriptions** | Agent | Creation | After PR scope differed | LLM reconciliation at landing |
| **Implementation Context** | Agent | Creation | After PR reveals new arch info | LLM reconciliation at landing |
| **Exploration Notes** | Agent at creation | Creation | Never (historical artifact) | Immutable |
| **Related Documentation** | Agent | Creation | When new docs discovered | LLM reconciliation at landing |
| ~~Current Focus~~ | ~~Agent~~ | ~~Creation~~ | ~~Dropped~~ | ~~Redundant with `find_next_step()`~~ |

**Key principle**: Sections split into three tiers:
1. **Mechanical** (exec-managed): Roadmap status/PR cells. Deterministic, no LLM needed.
2. **Reconcilable** (LLM-managed): Design Decisions, Implementation Context, step descriptions. Updated when reality diverges from what's written.
3. **Immutable** (historical): Exploration Notes. Snapshot from creation time, never modified.

## Part 2: Reconciliation Protocol

### When: After Every PR Landing

The `objective-update-with-landed-pr` skill is the primary reconciliation trigger. After mechanical step updates, the subagent performs **prose reconciliation**.

### What the Subagent Audits

The subagent reads:
- The objective body (post-mechanical-update, so roadmap is already current)
- The PR title, description, and plan body

And checks each reconcilable section for contradictions:

| Contradiction Type | Example | Section to Update |
|-------------------|---------|-------------------|
| **Decision override** | Objective says "Use polling", PR implemented WebSockets | Design Decisions |
| **Scope change** | Step says "Add 3 methods", PR only needed 2 | Step description in roadmap |
| **Architecture drift** | Context says "config in config.py", PR moved it to settings/ | Implementation Context |
| **Constraint invalidation** | Requirement listed is no longer valid | Implementation Context |
| **New discovery** | PR revealed a caching bug affecting future steps | Implementation Context or new Design Decision |

### How the Subagent Reports

The action comment gains a new optional subsection: **Body Reconciliation**.

```markdown
## Action: [Title]

**Date:** YYYY-MM-DD
**PR:** #123
**Phase/Step:** 1.3

### What Was Done
- [...]

### Lessons Learned
- [...]

### Roadmap Updates
- Step 1.3: pending → done

### Body Reconciliation
- **Design Decisions**: Updated decision #2 - changed from "polling" to "WebSocket" based on latency requirements discovered during implementation
- **Implementation Context**: Updated "Current Architecture" - config module was split into config/settings.py and config/defaults.py
- **Step 2.1**: Narrowed scope from "Add 3 gateway methods" to "Add 2 gateway methods" (third was unnecessary)
```

If nothing is stale, the subsection is omitted entirely (not "No changes needed").

### When: At Next-Step Pickup (Lighter Touch)

When `objective-next-plan` runs, the agent reads the full objective body to plan the next step. Add explicit instructions:

> Before creating the plan, scan the objective body for context that may be stale. The Implementation Context section was last reconciled when the previous PR landed - the codebase may have changed since then from other work. If you discover stale information during your exploration, note it and update the objective body before proceeding with planning.

This is a lighter reconciliation - it happens naturally during the agent's codebase exploration phase. We just need to make it explicit in the skill instructions.

## Part 3: Format Changes

### Drop "Current Focus"

Remove from all templates and references. Replace with nothing - `find_next_step()` from `objective_roadmap_shared.py` already computes this, and agents reading the roadmap can see what's pending.

**Files to edit (remove Current Focus):**

| File | Change |
|------|--------|
| `.claude/skills/objective/references/format.md` | Remove section from template (L82-84), remove from "What to Update" (L165), remove phase completion pattern (L348), remove from example (L286-288) |
| `.claude/skills/objective/references/workflow.md` | Remove from template (L85-87), remove from "Getting Up to Speed" (L165), remove from "Designing for Session Handoff" (L226), remove from "Best Practices" (L255) |
| `.claude/skills/objective/references/closing.md` | Remove Trigger 2 entirely (L20-33), remove from pre-closing checklist (L78), remove lingering anti-pattern (L154) |
| `.claude/skills/objective/SKILL.md` | Remove from template (L92-94), remove from post-action instruction (L114) |
| `.claude/commands/erk/objective-create.md` | Remove from steelthread template (implicit in template block), remove from perpetual objectives (L272-274) |
| `.claude/commands/erk/land.md` | Remove from post-land instruction (L143) |
| `docs/learned/objectives/objective-lifecycle.md` | Remove from mutation descriptions (L212, L224, L342) |
| `docs/learned/objectives/roadmap-mutation-patterns.md` | Remove reference (L62) |

### Add "Body Reconciliation" to Action Comment Template

In `format.md`, add the optional subsection to the action comment template (after "Roadmap Updates"):

```markdown
### Body Reconciliation (if applicable)
- **[Section name]**: [What changed and why]
```

And add to the "When to Update" list:
- After landing a PR that diverged from what the objective described

### Update "What to Update in Issue Body"

In `format.md` L160-167, replace the Current Focus bullet with reconciliation guidance:

```markdown
After posting an action comment, update these sections in the issue body:

- **Roadmap tables** - Change step statuses, add PR links (via exec commands)
- **Design Decisions** - Revise any decisions that were overridden during implementation
- **Implementation Context** - Correct architecture descriptions that no longer match reality
- **Step descriptions** - Adjust scope if what was built differs from what was planned
```

## Part 4: Skill Updates

### `.claude/commands/erk/objective-update-with-landed-pr.md`

Rewrite subagent instructions. New flow:

| Step | Type | What |
|------|------|------|
| 1 | Exec | `erk exec objective-update-context` → fetch context |
| 2 | Exec | `erk exec objective-mark-landed` → mark steps done deterministically |
| 3 | **LLM** | **Prose reconciliation**: Compare objective body against PR/plan. Identify stale Design Decisions, Implementation Context, step descriptions. Compose action comment (with Body Reconciliation subsection) + updated body. |
| 4 | Exec | `erk exec post-issue-comment --body-file <tmp>` → post action comment |
| 5 | Exec | `erk exec update-issue-body --body-file <tmp>` → post reconciled body (skip if no prose changes) |
| 6 | Exec | `erk exec close-issue-with-comment` if `all_done` from step 2 |

The LLM reconciliation instructions should be explicit:

> **Reconciliation Checklist:**
> 1. Read each Design Decision. Did the PR override or refine any? If so, update the decision text and log in Body Reconciliation.
> 2. Read Implementation Context. Does the architecture description still match reality after this PR? If not, correct it.
> 3. Read step descriptions for upcoming steps. Did this PR change the landscape such that future step descriptions need adjustment?
> 4. If nothing is stale, skip Body Reconciliation subsection and skip body update.

### `.claude/commands/erk/objective-next-plan.md`

Add reconciliation awareness when picking up next step:

> Before creating the plan, scan the objective's reconcilable sections (Design Decisions, Implementation Context) for information that may have become stale since the last PR landing. If your codebase exploration reveals contradictions, update the objective body and post an "Action: Reconciled objective context" comment before proceeding with planning.

### `.claude/skills/objective/SKILL.md`

Update key design principles to include:
- **Body stays current via reconciliation** - After every PR landing, agents audit prose sections against what was actually implemented and correct stale information.

Update workflow summary to mention reconciliation as part of the landing step.

### `.claude/skills/objective/references/updating.md`

Add reconciliation as a change type to the table:

| Change Type | Comment | Body Update |
|---|---|---|
| Reconcile after PR | "Action: [Title]" with Body Reconciliation subsection | Update stale sections |

## Part 5: Documentation Updates

### `docs/learned/objectives/objective-lifecycle.md`

Add a section on the reconciliation lifecycle:
- Define the three section tiers (mechanical, reconcilable, immutable)
- Document when reconciliation happens
- Document what the agent checks

### `docs/learned/objectives/roadmap-mutation-patterns.md`

Update to reflect that body mutations now include prose reconciliation, not just roadmap mechanics.

## Dependencies

This plan depends on plan **#6889** (exec commands) for:
- `erk exec objective-mark-landed` - deterministic step marking
- `erk exec post-issue-comment` - gateway-backed comment posting

The exec commands handle the mechanical parts. This plan handles the content lifecycle and reconciliation protocol.

## Verification

1. Review updated templates for consistency - no Current Focus references remain
2. Review action comment template includes Body Reconciliation subsection
3. Run `/erk:objective-update-with-landed-pr` end-to-end on a real objective - verify the subagent performs prose reconciliation
4. Run `/erk:objective-next-plan` - verify the agent checks for stale context before planning