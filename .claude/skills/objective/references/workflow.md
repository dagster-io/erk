# Objective Workflow Reference

Detailed procedures for creating objectives, spawning plans, and resuming work.

## Contents

- [Creating a New Objective](#creating-a-new-objective)
- [Spawning Erk-Plans](#spawning-erk-plans)
- [Resuming Work on an Objective](#resuming-work-on-an-objective)
- [Structuring for Steelthread Development](#structuring-for-steelthread-development)
- [Best Practices](#best-practices)

For updating and closing objectives, see:

- [updating.md](updating.md) - Two-step update workflow
- [closing.md](closing.md) - Closing triggers and procedures

## Creating a New Objective

### When to Create

Create an objective when:

- A goal requires 2+ related PRs to complete
- Work spans multiple sessions or days
- Lessons learned should be captured for future reference
- Coordination across related changes is needed

Do NOT create an objective for:

- Single PR implementations (use erk-plan instead)
- Quick fixes or one-off changes
- Exploratory work without clear deliverables

### Creation Steps

1. **Define the goal** - What does success look like?
2. **Identify phases** - Logical groupings of related work
3. **Structure for steelthread** - Split phases into sub-phases (XA, XB, XC)
4. **Break into steps** - Specific tasks within each sub-phase
5. **Add test statements** - Each sub-phase needs "Test: [acceptance criteria]"
6. **Lock design decisions** - Choices that guide implementation

```bash
gh issue create \
  --title "Objective: [Descriptive Title]" \
  --label "erk-objective" \
  --body "$(cat <<'EOF'
# Objective: [Title]

> [Summary]

## Goal

[End state]

## Design Decisions

1. **[Name]**: [Decision]

## Roadmap

### Phase 1A: [Name] Steelthread (1 PR)

Minimal vertical slice proving the concept works.

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1A.1 | [Minimal infrastructure] | pending | |
| 1A.2 | [Wire into one command] | pending | |

**Test:** [End-to-end acceptance test for steelthread]

### Phase 1B: Complete [Name] (1 PR)

Fill out remaining functionality.

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1B.1 | [Extend to remaining commands] | pending | |
| 1B.2 | [Full test coverage] | pending | |

**Test:** [Full acceptance criteria]

## Current Focus

**Next action:** [First step]
EOF
)"
```

### Naming Conventions

- Title: `Objective: [Verb] [What]` (e.g., "Objective: Unify Gateway Testing")
- Sub-phases: `Phase NA: [Noun] [Type] (1 PR)` (e.g., "Phase 1A: Git Gateway Steelthread (1 PR)")
- Steps: `NA.M` numbering (e.g., 1A.1, 1A.2, 1B.1)

## Spawning Erk-Plans

Objectives coordinate work; erk-plans execute it. Spawn an erk-plan for individual steps.

### When to Spawn

Spawn an erk-plan when:

- A roadmap step is ready to implement
- The step is well-defined and scoped
- Implementation can complete in one PR

### Spawning Steps

1. **Identify the step** - Which roadmap step to implement
2. **Create the plan** - Reference the objective

```bash
# Create an erk-plan for a specific objective step
erk plan create \
  --title "[Step description]" \
  --body "$(cat <<'EOF'
## Context

Part of Objective #<issue-number>, Step <N.M>.

[Link to objective]: https://github.com/<owner>/<repo>/issues/<issue-number>

## Goal

[Specific deliverable for this step]

## Implementation

[Plan details]
EOF
)"
```

3. **Update objective** - Mark step as in-progress

### After Plan Completion

1. **Merge the PR** from the erk-plan
2. **Post action comment** on the objective (see [updating.md](updating.md))
3. **Update objective body** - step status, link PR
4. **Check for closing** - If all steps done, see [closing.md](closing.md)

## Resuming Work on an Objective

### Finding the Objective

```bash
# List open objectives
gh issue list --label "erk-objective" --state open

# View specific objective
gh issue view <issue-number>

# View with comments
gh issue view <issue-number> --comments
```

### Getting Up to Speed

1. **Read the issue body** - Current state and design decisions
2. **Read recent comments** - Latest actions and lessons
3. **Check "Current Focus"** - What should happen next
4. **Review linked PRs** - Context from completed work

### Continuing Work

1. **Identify next step** from roadmap
2. **Create erk-plan** if needed for implementation
3. **Work on the step**
4. **Post action comment** when done (see [updating.md](updating.md))
5. **Update body** with new status

## Structuring for Steelthread Development

### The Steelthread Pattern

Each major phase should be split into sub-phases:

1. **XA: Steelthread** - Minimal vertical slice (1 PR)
   - Just enough infrastructure to prove concept
   - Wire into ONE command/feature as proof
   - Includes acceptance test

2. **XB: Complete** - Fill out functionality (1 PR)
   - Extend to remaining commands
   - Full test coverage
   - Handle edge cases

3. **XC: Integration** (if needed) - Wire into rest of system (1 PR)
   - Backward compatibility
   - Migration from old approach

### Signs Your Phase Needs Splitting

Split a phase if:

- It has high technical risk (unproven patterns, new integrations, complex logic)
- Steps mix infrastructure + wiring + commands
- You can't describe a single acceptance test
- Multiple independent concerns are bundled

### Naming Convention

- `Phase 1A` not `Phase 1.1` (sub-phases, not sub-steps)
- Include "(1 PR)" to signal expected scope
- Name should describe the slice: "Steelthread", "Complete", "Integration"

### Each Sub-Phase Must Have

1. **Test statement** - "Test: [what proves this works]"
2. **Coherent scope** - All steps relate to same concern
3. **Shippable state** - System works after merge

## Designing for Session Handoff

Objectives coordinate work across multiple sessions. The body should be self-contained enough that any session can pick up a phase and implement without re-exploring the codebase.

### What the Body Should Include

1. **Design decisions** - Locked choices that guide implementation
2. **Implementation context** - Architecture, patterns, requirements
3. **Clear roadmap** - What to do, in what order
4. **Current focus** - Exactly what's next

### What to Avoid

- **Prescriptive code skeletons** - Let implementing agent design the solution
- **Incomplete context** - "See the codebase" is not helpful
- **Stale information** - Keep body current after every change

### The Two-Step Discipline

Every change to the objective follows two steps:

1. **Comment first** - Log what changed and why (changelog entry)
2. **Body second** - Update to reflect new state (source of truth)

This applies to:

- Completing steps (obvious)
- Adding context (often forgotten)
- Refining decisions (often forgotten)
- Adding phases (often forgotten)

## Best Practices

### Keep the Body Current

The issue body is the source of truth. After every significant change:

- Update step statuses
- Update "Current Focus"
- Add new design decisions if any

### Write Actionable Lessons

Bad: "This was tricky"
Good: "The API requires pagination for lists > 100 items; always check response headers"

### Link Everything

- Link PRs in the roadmap table
- Link related issues in action comments
- Link erk-plans spawned from the objective

### Don't Over-Engineer

- Start with minimal phases/steps
- Add detail as work progresses
- Split steps when needed, not preemptively
