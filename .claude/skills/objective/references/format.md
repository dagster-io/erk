# Objective Format Reference

Complete templates and examples for objective issues.

## Contents

- [Issue Body Template](#issue-body-template)
- [Action Comment Template](#action-comment-template)
  - [When to Update](#when-to-update)
  - [What to Update in Issue Body](#what-to-update-in-issue-body)
- [Example: Steelthread-Structured Objective](#example-steelthread-structured-objective)
- [Common Patterns](#common-patterns)
- [Update Examples](#update-examples)

## Issue Body Template

The issue body represents the **current state** of the objective. Update it as progress is made.

```markdown
# Objective: [Title]

> [1-2 sentence summary of what this objective achieves]

## Goal

[What success looks like - concrete end state. Be specific about deliverables.]

## Design Decisions

Locked decisions that guide all related work:

1. **[Decision name]**: [What was decided and why]
2. **[Decision name]**: [What was decided and why]

## Roadmap

### Phase 1A: [Name] Steelthread (1 PR)

Minimal vertical slice proving the concept works.

| Step | Description              | Status  | PR  |
| ---- | ------------------------ | ------- | --- |
| 1A.1 | [Minimal infrastructure] | pending |     |
| 1A.2 | [Wire into one command]  | pending |     |

**Test:** [End-to-end acceptance test for steelthread]

### Phase 1B: Complete [Name] (1 PR)

Fill out remaining functionality.

| Step | Description                    | Status  | PR  |
| ---- | ------------------------------ | ------- | --- |
| 1B.1 | [Extend to remaining commands] | pending |     |
| 1B.2 | [Full test coverage]           | pending |     |

**Test:** [Full acceptance criteria]

## Implementation Context

### Current Architecture

[File locations, what exists now, how things are wired]

### Patterns to Follow

[References to existing patterns - NOT code skeletons]

### Technical Requirements

[What methods/components need what behavior, error message requirements]

### Test Strategy

[What needs testing, test helper considerations]

**Note:** Provide context and references, not prescriptive code.
The implementing agent should have freedom to design the solution
while having all the context they need.

## Current Focus

**Next action:** [Exactly what should happen next]
```

### Status Values

- `pending` - Not yet started
- `in-progress` - Currently being worked on
- `done` - Completed
- `blocked` - Waiting on external dependency
- `skipped` - Decided not to do

## Action Comment Template

Each action comment logs work done and lessons learned. Post one comment per significant action.

```markdown
## Action: [Brief title - what was accomplished]

**Date:** YYYY-MM-DD
**PR:** #123 (if applicable)
**Phase/Step:** 1.2

### What Was Done

- [Concrete action 1]
- [Concrete action 2]
- [Concrete action 3]

### Lessons Learned

- [Insight that should inform future work]
- [Technical discovery]
- [Process improvement]

### Roadmap Updates

- Step 1.2: pending → done
- [Any other status changes]
```

### Action Comment Guidelines

- **One action per comment** - Atomic logging, not batch updates
- **Lessons are mandatory** - Even small insights matter
- **Be concrete** - "Fixed auth flow" not "Made improvements"
- **Link PRs** - Always reference the PR if applicable

### Action Title Format

Use past-tense to indicate completed action:

- ✅ "Action: Added Implementation Context"
- ✅ "Action: Completed Phase 1A"
- ✅ "Action: Refined error message requirements"
- ❌ "Implementation Context" (not an action)
- ❌ "Phase 1A" (not descriptive)

### When to Update

Update after:

- Completing one or more roadmap steps
- Merging a related PR
- **Adding implementation context**
- **Adding or refining design decisions**
- **Adding new phases or steps**
- Hitting a blocker that changes the plan
- Discovering new work that needs adding to the roadmap
- Changing direction or design decisions

Do NOT update for:

- Minor progress within a step
- Work-in-progress status
- Questions (use PR comments instead)

### What to Update in Issue Body

After posting an action comment, update these sections in the issue body:

- **Roadmap tables** - Change step statuses, add PR links
- **Current Focus** - Update "Next action" to reflect new state
- **Design Decisions** - Add any new decisions that emerged
- **Implementation Context** - Add reference material discovered

### Adding Context (Non-Completion Action)

When adding implementation context or refining the objective:

**Action Comment:**

```markdown
## Action: Added Implementation Context

**Date:** 2026-01-01

### What Was Done

- Added current architecture details (file locations, existing patterns)
- Documented patterns to follow with references
- Listed ABC methods by behavior category
- Added error message requirements
- Outlined test strategy

### Lessons Learned

- [Any insights from the exploration]

### Why

Enable session handoff - any future session can implement without re-exploring.
```

**Body Changes:**

- Added "Implementation Context" section with all details

## Example: Steelthread-Structured Objective

### Issue Body

```markdown
# Objective: Unified Gateway Testing

> Establish consistent testing patterns across all gateway ABCs (Git, GitHub, Graphite).

## Goal

All gateway ABCs have:

- Comprehensive fake implementations
- Dry-run implementations for previewing mutations
- Consistent test patterns documented

## Design Decisions

1. **Fakes over mocks**: Use stateful fake implementations, not mock objects
2. **Dry-run via DI**: Inject dry-run wrappers instead of boolean flags
3. **Test in isolation**: Gateway tests don't hit real services
4. **Steelthread-first**: Each gateway starts with minimal fake, then expands

## Roadmap

### Phase 1A: Git Gateway Steelthread (1 PR)

| Step | Description                                         | Status | PR   |
| ---- | --------------------------------------------------- | ------ | ---- |
| 1A.1 | Create FakeGit with just `commit()` and `get_log()` | done   | #301 |
| 1A.2 | Wire into one test as proof of concept              | done   | #301 |

**Test:** One gateway test runs with FakeGit instead of mocking.

### Phase 1B: Complete Git Gateway (1 PR)

| Step | Description                                            | Status | PR   |
| ---- | ------------------------------------------------------ | ------ | ---- |
| 1B.1 | Add remaining FakeGit methods (branch, checkout, etc.) | done   | #305 |
| 1B.2 | Add DryRunGit wrapper                                  | done   | #305 |
| 1B.3 | Migrate all Git tests to use FakeGit                   | done   | #305 |

**Test:** All git gateway tests use FakeGit, no subprocess mocking.

### Phase 2A: GitHub Gateway Steelthread (1 PR)

| Step | Description                               | Status  | PR  |
| ---- | ----------------------------------------- | ------- | --- |
| 2A.1 | Create FakeGitHub with just `create_pr()` | pending |     |
| 2A.2 | Wire into PR submission test              | pending |     |

**Test:** PR creation test uses FakeGitHub.

### Phase 2B: Complete GitHub Gateway (1 PR)

| Step | Description                      | Status  | PR  |
| ---- | -------------------------------- | ------- | --- |
| 2B.1 | Add remaining FakeGitHub methods | pending |     |
| 2B.2 | Add DryRunGitHub wrapper         | pending |     |

**Test:** All GitHub gateway tests use FakeGitHub.

## Implementation Context

### Current Architecture

Gateway ABC pattern uses abstract base classes with real and fake implementations.
See `erk/gateways/git/` for the full pattern.

### Patterns to Follow

- Gateway ABC: `erk/gateways/git/` shows complete pattern
- Fakes need to track branch state, not just commits

### Technical Requirements

- FakeGitHub must implement all methods from GitHub ABC
- State tracking for PRs, issues, and reviews

### Test Strategy

- Tests should use FakeGitHub instead of subprocess mocking
- One integration test per major workflow

## Current Focus

**Next action:** Create FakeGitHub with minimal `create_pr()` method
```

### Action Comments

```markdown
## Action: Git Gateway Steelthread Complete

**Date:** 2025-01-15
**PR:** #301
**Phase/Step:** 1A

### What Was Done

- Created minimal FakeGit with just commit() and get_log()
- Wired into one test as proof of concept
- Validated the fake pattern works

### Lessons Learned

- Fakes need to track branch state, not just commits
- Starting minimal reveals what's actually needed
- One working test proves the pattern before investing more

### Roadmap Updates

- Phase 1A: all steps → done
```

```markdown
## Action: Completed Git Gateway

**Date:** 2025-01-18
**PR:** #305
**Phase/Step:** 1B

### What Was Done

- Added remaining FakeGit methods (branch, checkout, etc.)
- Created DryRunGit wrapper
- Migrated all Git tests to use FakeGit

### Lessons Learned

- DryRunGit should inherit from Git ABC for type safety
- Logging format should match real git output for user familiarity
- Read operations should delegate to real implementation

### Roadmap Updates

- Phase 1B: all steps → done
```

## Common Patterns

### Completing a Phase

When all steps in a phase are done:

1. Mark phase header with ✅ (e.g., "### Phase 1: Git Gateway ✅")
2. Update "Current Focus" to point to next phase
3. Consider adding a summary note under the phase

### Blocking Dependencies

When a step is blocked:

```markdown
| 2.3 | Integrate with CI | blocked | | <!-- Blocked on #400 -->
```

Log the blocker in an action comment:

```markdown
## Action: Identified CI integration blocker

**Date:** 2025-01-20
**Phase/Step:** 2.3

### What Was Done

- Attempted CI integration
- Discovered missing permissions in workflow

### Lessons Learned

- Need GITHUB_TOKEN with contents:write for this feature
- Must coordinate with platform team

### Roadmap Updates

- Step 2.3: pending → blocked (waiting on #400)
```

### Skipping Steps

When deciding to skip a step:

```markdown
## Action: Decided to skip Graphite dry-run

**Date:** 2025-01-22
**Phase/Step:** 3.2

### What Was Done

- Analyzed Graphite API usage patterns
- Found that all Graphite operations are read-only in our codebase

### Lessons Learned

- Dry-run only needed for mutation operations
- YAGNI principle applies

### Roadmap Updates

- Step 3.2: pending → skipped (no mutations to preview)
```

### Splitting Steps

When a step turns out to need subdivision:

```markdown
## Action: Split authentication step

**Date:** 2025-01-25
**Phase/Step:** 2.1

### What Was Done

- Started work on FakeGitHub
- Realized authentication is complex enough to warrant separate step

### Lessons Learned

- OAuth vs PAT handling differs significantly
- Better to have granular steps than monolithic ones

### Roadmap Updates

- Step 2.1 split into:
  - 2.1a: FakeGitHub core (pending)
  - 2.1b: FakeGitHub authentication (pending)
```

Then update the issue body to reflect the new structure.

## Update Examples

Real examples of the two-step update workflow in action.

### Completing Multiple Phases at Once

When a single PR completes substantial work across multiple phases:

**Action Comment:**

```markdown
## Action: Phase 2-6 Completed - Kit Infrastructure Deleted

**Date:** 2025-12-30
**PR:** #3485
**Phase/Step:** 2.1-6.3

### What Was Done

- Deleted src/erk/kits/ directory (~4,200 lines)
- Deleted packages/erk-kits/ package entirely
- Removed all kit-related CLI commands
- Fixed 16 exec scripts to use new imports

**Impact:** ~21,500 lines deleted across 203 files

### Lessons Learned

- Deletion was straightforward once utilities were relocated in Phase 1
- Discovered artifact sync needs to be restored separately (new Phase 7)
- Large deletions benefit from capturing impact metrics

### Roadmap Updates

- Phase 2-6: all steps → done (#3485)
- Added new Phase 7 for follow-up work discovered during deletion
```

**Body Changes:**

- Changed all Phase 2-6 step statuses from `pending` to `done`
- Added PR #3485 link to each completed step
- Added new Phase 7 section with steps for discovered follow-up work
- Updated "Current Focus" to "Complete Phase 7 - restore artifact sync"

### Adding Discovered Work

When implementation reveals additional scope:

**Action Comment:**

```markdown
## Action: Discovered Follow-up Work During Kit Deletion

**Date:** 2025-12-30
**Phase/Step:** N/A (scope expansion)

### What Was Done

- Completed main kit deletion
- Discovered that artifact sync functionality needs restoration
- Artifact sync was startup check that prompted `erk init` if stale

### Lessons Learned

- Deleting infrastructure often reveals hidden dependencies
- Better to add new phase than expand existing completed ones
- Document what the deleted code did to guide restoration

### Roadmap Updates

- Added Phase 7: Artifact Sync Restoration
  - 7.1: Implement startup version check
  - 7.2: Restore artifact copy mechanism
```

### Updating After a Blocker Resolves

**Action Comment:**

```markdown
## Action: CI Integration Blocker Resolved

**Date:** 2025-01-22
**PR:** #412
**Phase/Step:** 2.3

### What Was Done

- Platform team merged #400 with new permissions
- Implemented CI integration using new GITHUB_TOKEN scope
- Added workflow file and tests

### Lessons Learned

- Document blockers in roadmap table with HTML comments
- Check GitHub Actions permissions early in planning
- Platform team turnaround was faster than expected

### Roadmap Updates

- Step 2.3: blocked → done
```

**Body Changes:**

- Changed step 2.3 status from `blocked` to `done`
- Removed HTML comment about blocker
- Added PR #412 link
- Updated "Current Focus" to next pending step
