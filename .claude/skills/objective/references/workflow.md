# Objective Workflow Reference

Detailed procedures for creating, updating, and closing objectives.

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
3. **Break into steps** - Specific tasks within each phase
4. **Lock design decisions** - Choices that guide implementation

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

### Phase 1: [Name]

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | [Task] | pending | |

## Current Focus

**Next action:** [First step]
EOF
)"
```

### Naming Conventions

- Title: `Objective: [Verb] [What]` (e.g., "Objective: Unify Gateway Testing")
- Phases: `Phase N: [Noun Phrase]` (e.g., "Phase 1: Git Gateway")
- Steps: `N.M` numbering (e.g., 1.1, 1.2, 2.1)

## Updating an Objective

### After Completing Work

1. **Post action comment** - Log what was done and lessons learned
2. **Update issue body** - Change step status, update "Current Focus"

```bash
# 1. Post action comment
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Action: [Title]

**Date:** $(date +%Y-%m-%d)
**PR:** #123
**Phase/Step:** 1.2

### What Was Done
- [Action 1]
- [Action 2]

### Lessons Learned
- [Lesson 1]

### Roadmap Updates
- Step 1.2: pending → done
EOF
)"

# 2. Update issue body (edit in browser or use gh issue edit)
gh issue view <issue-number> --web
```

### Updating the Body

Edit the issue body to reflect:

- **Step status changes** - pending → done, etc.
- **Current Focus** - Next action to take
- **New design decisions** - If any emerged during work
- **Key Technical Details** - Reference material discovered

Keep the body as the source of truth for current state.

### When to Post Action Comments

Post a comment after:

- Completing a roadmap step
- Merging a related PR
- Making a significant discovery
- Hitting a blocker
- Changing direction

Do NOT post comments for:

- Minor progress updates
- Work-in-progress status
- Questions (use PR comments instead)

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
2. **Post action comment** on the objective
3. **Update objective body** - step status, link PR

## Closing an Objective

### When to Close

Close an objective when:

- All roadmap steps are done/skipped
- The goal has been achieved
- The objective is abandoned (document why)

### Closing Steps

1. **Post final action comment** - Summarize outcomes
2. **Verify body is current** - All statuses updated
3. **Close the issue**

```bash
# Post final summary
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Action: Objective Complete

**Date:** $(date +%Y-%m-%d)

### Summary
[What was achieved overall]

### Key Outcomes
- [Outcome 1]
- [Outcome 2]

### Lessons for Future Objectives
- [Meta-lesson about the process]
EOF
)"

# Close the issue
gh issue close <issue-number>
```

### Abandoning an Objective

If abandoning, document why:

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Action: Objective Abandoned

**Date:** $(date +%Y-%m-%d)

### Reason
[Why the objective is being abandoned]

### Completed Work
- [What was done before abandoning]

### Lessons Learned
- [Insights from the work]

### Disposition
- [What happens to any in-progress work]
EOF
)"

gh issue close <issue-number> --reason "not planned"
```

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
4. **Post action comment** when done
5. **Update body** with new status

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

### Review Before Closing

Before closing, verify:

- All steps are done/skipped with reasons
- Action comments capture key lessons
- Body reflects final state
- Related PRs are merged
