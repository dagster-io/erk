# Plan: Add "Never Run gt sync" Tripwire

## Objective

Add a tripwire rule documenting that agents should never run `gt sync` or `gt repo sync` on the user's behalf.

## Implementation

### File to Modify

`docs/agent/erk/auto-restack.md`

### Change

Add a tripwire to the frontmatter:

```yaml
tripwires:
  - action: "running gt sync or gt repo sync on user's behalf"
    warning: "NEVER run 'gt sync' or 'gt repo sync' automatically. This command synchronizes all Graphite branches with GitHub and can delete branches, modify stack relationships, and make irreversible changes. The user must run this command explicitly."
```

### Rationale

- `auto-restack.md` is the most relevant file - it covers Graphite stack operations
- Adding to frontmatter means it will be auto-generated into `docs/agent/tripwires.md`
- The tripwire pattern is the established way to document forbidden agent actions

### After Implementation

Run `dot-agent docs sync` to regenerate the tripwires.md file.