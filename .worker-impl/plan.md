# Plan: Doc Reference Injection During Planning

## Objective

Ensure planners capture relevant documentation references in plans so implementing agents don't need to rediscover them.

## Problem Statement

In the analyzed session, the implementing agent didn't discover existing documentation (`push-down-pattern.md`, `kit-cli-testing.md`) because:
- The plan contained specific steps - agent was in "execution mode" not "discovery mode"
- No mechanism carries documentation context from planning phase to implementation phase

**Key insight**: The planner already knows which docs are relevant - they discovered them during exploration. That knowledge should be captured in the plan.

## Solution

Two changes:

1. **Planning guidance**: Instruct planners to include a "Related Documentation" section listing docs/skills relevant to implementation
2. **Implementation consumption**: Update `/erk:plan-implement` to load docs/skills from that section before starting

## Design

### Related Documentation Section Format

```markdown
## Related Documentation

Load these before implementing:

**Skills:**
- `dignified-python-313` - Python patterns for this codebase
- `fake-driven-testing` - Testing architecture

**Docs:**
- [Kit CLI Push Down Pattern](docs/agent/kits/push-down-pattern.md) - Moving logic from agent to kit CLI
- [Kit CLI Testing](docs/agent/testing/kit-cli-testing.md) - DotAgentContext.for_test() patterns
```

## Implementation Steps

### 1. Update AGENTS.md planning guidance

Add to Tier 4 section (Documentation Lookup):

```markdown
### Including Documentation in Plans

When creating implementation plans, include a "Related Documentation" section listing:
- Skills to load before implementing
- Docs relevant to the implementation approach

This ensures implementing agents have access to documentation you discovered during planning.
```

### 2. Update `/erk:plan-implement` command

Modify `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`:

Add new step after "Step 2: Read the Plan File":

```markdown
### Step 2.5: Load Related Documentation

If the plan contains a "Related Documentation" section:

1. **Load skills**: For each skill listed, use the Skill tool to load it
2. **Read docs**: For each doc listed, use the Read tool to load it
3. **Keep context**: This documentation informs your implementation approach

Example section to look for:
\`\`\`markdown
## Related Documentation

**Skills:**
- `dignified-python-313`

**Docs:**
- [Kit CLI Testing](docs/agent/testing/kit-cli-testing.md)
\`\`\`
```

## Files to Modify

1. `AGENTS.md` - Add guidance about including Related Documentation in plans
2. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md` - Add doc loading step

## Testing

- Manual verification: Create a plan with Related Documentation section, run `/erk:plan-implement`, verify docs are loaded

## Success Criteria

1. Planning guidance instructs planners to capture relevant docs
2. Implementing agents load docs specified in plans before starting
3. No new kit CLI commands or agents required - just guidance changes