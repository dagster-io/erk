# Updating an Objective

The update workflow has two steps that should **always happen together**:

1. **Post an action comment** - Captures what happened and lessons learned
2. **Update the issue body** - Reflects new roadmap state

Comment first (captures the moment), then body (reflects new state).

## When to Update

Update after:

- Completing one or more roadmap steps
- Merging a related PR
- Hitting a blocker that changes the plan
- Discovering new work that needs adding to the roadmap
- Changing direction or design decisions

Do NOT update for:

- Minor progress within a step
- Work-in-progress status
- Questions (use PR comments instead)

## The Two-Step Update

### Step 1: Post Action Comment

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
## Action: [Brief title - what was accomplished]

**Date:** $(date +%Y-%m-%d)
**PR:** #123 (if applicable)
**Phase/Step:** 1.2 (or range like 2.1-2.6)

### What Was Done
- [Concrete action 1]
- [Concrete action 2]

### Lessons Learned
- [Insight that should inform future work]

### Roadmap Updates
- Step 1.2: pending → done
- [Any other status changes]
EOF
)"
```

### Step 2: Update Issue Body

Open the issue in browser to edit:

```bash
gh issue view <issue-number> --web
```

Update these sections:

- **Roadmap tables** - Change step statuses, add PR links
- **Current Focus** - Update "Next action" to reflect new state
- **Design Decisions** - Add any new decisions that emerged
- **Key Technical Details** - Add reference material discovered

## Common Update Scenarios

### Completing a Phase

When all steps in a phase are done:

1. Mark phase header with ✅ (e.g., "### Phase 1: Git Gateway ✅")
2. Update "Current Focus" to point to next phase
3. Consider adding a summary note under the phase

### Blocking a Step

```markdown
### Roadmap Updates

- Step 2.3: pending → blocked (waiting on #400)
```

Update body to show blocked status:

```markdown
| 2.3 | Integrate with CI | blocked | | <!-- Blocked on #400 -->
```

### Adding New Work Mid-Objective

1. Post action comment explaining the scope change
2. Add new steps to the roadmap in the body
3. Update phase numbering if needed

### Multiple PRs in One Update

When a single session completes multiple steps or phases:

```markdown
**PR:** #3485
**Phase/Step:** 2.1-6.3

### Roadmap Updates

- Phase 2: all steps → done
- Phase 3: all steps → done
- Phase 4-6: all steps → done
```

### Discovering Follow-up Work

When implementation reveals additional work needed:

1. Post action comment documenting the discovery
2. Add new phase or steps to the roadmap
3. Don't expand scope silently - make additions visible
