# Objective Format Reference

Complete templates and examples for objective issues.

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

### Phase 1: [Name]

| Step | Description     | Status  | PR  |
| ---- | --------------- | ------- | --- |
| 1.1  | [Specific task] | pending |     |
| 1.2  | [Specific task] | pending |     |

### Phase 2: [Name]

| Step | Description     | Status  | PR  |
| ---- | --------------- | ------- | --- |
| 2.1  | [Specific task] | pending |     |
| 2.2  | [Specific task] | pending |     |

## Key Technical Details

[Reference material: code snippets, state formats, architectural notes, etc.
Include anything that would be useful when working on related plans.]

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

## Example: Real Objective

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

## Roadmap

### Phase 1: Git Gateway

| Step | Description                       | Status      | PR   |
| ---- | --------------------------------- | ----------- | ---- |
| 1.1  | Create FakeGit with stateful repo | done        | #301 |
| 1.2  | Add DryRunGit wrapper             | done        | #305 |
| 1.3  | Document patterns in AGENTS.md    | in-progress |      |

### Phase 2: GitHub Gateway

| Step | Description                     | Status  | PR  |
| ---- | ------------------------------- | ------- | --- |
| 2.1  | Create FakeGitHub with PR state | pending |     |
| 2.2  | Add DryRunGitHub wrapper        | pending |     |

### Phase 3: Graphite Gateway

| Step | Description                | Status  | PR  |
| ---- | -------------------------- | ------- | --- |
| 3.1  | Create FakeGraphite        | pending |     |
| 3.2  | Add DryRunGraphite wrapper | pending |     |

## Key Technical Details

Gateway ABC pattern uses abstract base classes with real and fake implementations.
See `erk/gateways/git/` for the full pattern. Key insight: fakes need to track
branch state, not just commits.

## Current Focus

**Next action:** Complete AGENTS.md documentation for gateway testing patterns
```

### Action Comments

```markdown
## Action: Created FakeGit with stateful repository

**Date:** 2025-01-15
**PR:** #301
**Phase/Step:** 1.1

### What Was Done

- Implemented FakeGit class with in-memory state
- Added commit, branch, checkout operations
- Created test fixtures for common scenarios

### Lessons Learned

- Fakes need to track branch state, not just commits
- Reset method essential for test isolation
- Consider adding assertion helpers (e.g., `assert_committed(msg)`)

### Roadmap Updates

- Step 1.1: pending → done
```

```markdown
## Action: Added DryRunGit wrapper

**Date:** 2025-01-18
**PR:** #305
**Phase/Step:** 1.2

### What Was Done

- Created DryRunGit that logs operations without executing
- Integrated with existing print_dry_run utility
- Added tests for all mutation methods

### Lessons Learned

- DryRunGit should inherit from Git ABC for type safety
- Logging format should match real git output for user familiarity
- Read operations should delegate to real implementation

### Roadmap Updates

- Step 1.2: pending → done
```

## Common Patterns

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
