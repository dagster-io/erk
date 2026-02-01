---
read-when: handling automated code review feedback, resolving conflicts between bot comments and plan requirements, implementing features flagged by automated reviewers
tripwires: 0
---

# Handling Contradictory Feedback from Automated Review

## The Problem

Automated review bots analyze code without understanding the broader context of the current plan or feature requirements. This can lead to false positives where the bot flags code that directly implements the plan's explicit goal.

## The Pattern

When automated review bots flag code that appears in your recent changes:

1. **Check plan intent first**: Read `.impl/plan.md` to understand the feature requirements
2. **Compare feedback to plan**: Does the bot's suggestion contradict the plan's explicit goal?
3. **Don't auto-apply changes**: If there's a contradiction, DO NOT automatically make the suggested changes
4. **Escalate to user**: Use `AskUserQuestion` to clarify before making any changes
5. **Document resolution**: Explain why the feedback was a false positive in the PR thread

## Real Example

**Plan goal**: "Add a print statement to the CLI entry point"

**Implementation**: Added `click.echo("Hello from erk")` to `main()` function

**Bot feedback**: "This appears to be a debug print statement that should be removed"

**Correct response**:

1. Agent recognized the contradiction with the plan
2. Asked user to clarify via `AskUserQuestion`
3. User confirmed the feature should be kept
4. Agent resolved the PR thread with explanation: "This is not a debug print—it's the core feature requested in the plan. The greeting is intentional user-facing output."

## Why This Matters

Automated reviewers are valuable for catching genuine issues, but they lack context about:

- Current plan requirements
- Intentional deviations from conventions
- Feature-specific exceptions to general rules

Always verify that automated feedback aligns with plan intent before applying changes. False positives waste time and can result in removing intentional features.

## Related Documentation

- [Bot Coordination](../pr-operations/bot-coordination.md) - Handling overlapping feedback from multiple bots
- [Plan Persistence](../planning/plan-persistence.md) - Understanding plan sources of truth
