# Plan: Add Forked Context to /local:objective-view

## Context

The `/local:objective-view` command currently runs inline in the parent conversation context. This means all intermediate tool calls (4 bash commands, a nested Task agent, formatting logic) consume parent context tokens. It should use `context: fork` like `/local:audit-doc` does, so only the final formatted output enters the parent context.

## Change

**File:** `.claude/commands/local/objective-view.md`

Add `context: fork` and `agent: general-purpose` to the YAML frontmatter:

```yaml
---
description: View progress and associations for an objective issue
context: fork
agent: general-purpose
---
```

No other changes needed - the command's instructions already produce a well-formatted final output that will be returned to the parent context.

## Verification

Run `/local:objective-view 8423` and confirm:
- It executes in a forked context (visible as a Task subagent in the output)
- The formatted objective summary is returned to the parent context
- The intermediate bash outputs don't pollute the parent context
