# Plan: Add Roadmap Node Description Reconciliation to Objective Updates

## Context

When `erk land` updates an objective after merging a PR, the system command `/erk:system:objective-update-with-landed-pr` runs two steps:

1. **Mechanical** (`erk exec objective-apply-landed-update`): Marks nodes as "done" with PR reference, but passes `description=None` — preserving the original description verbatim
2. **Prose reconciliation** (LLM): Updates stale design decisions in the objective's prose body comment

**The gap:** Node descriptions in the YAML roadmap are never updated. A node that says "Add `@json_output` decorator" stays that way even after the PR implemented it as `@json_command`. The contradiction table in Step 2 mentions "Node description in roadmap" as a scope change type, but never tells the LLM *how* to act on it — there's no instruction to call `erk exec update-objective-node --description`.

The tooling already exists — `update-objective-node` accepts `--description` and handles the full YAML + comment table re-render. The only change needed is in the system command's instructions.

## Changes

**Single file:** `.claude/commands/erk/system/objective-update-with-landed-pr.md`

### 1. Add "Naming divergence" row to the contradiction table (line 83)

Add after the "Scope change" row:

```markdown
| **Naming divergence**       | Node says `@json_output`, PR implemented `@json_command`     | Node description (via `update-objective-node --description`) |
```

### 2. Update "Scope change" action column (line 83)

Change from:
```
| **Scope change**            | Node says "Add 3 methods", PR only needed 2                  | Node description in roadmap                   |
```
To:
```
| **Scope change**            | Node says "Add 3 methods", PR only needed 2                  | Node description (via `update-objective-node --description`) |
```

### 3. Add node description reconciliation instructions after the contradiction table

Insert after the table (after line 87), before the "If prose reconciliation found stale sections" paragraph:

```markdown
**Node description reconciliation:** For each node in `roadmap.phases[].nodes[]`, compare the `description` against what the PR actually implemented:

- **Done nodes** (from `node_updates` in Step 1): Did the implementation rename, reshape, or change scope? Update if the description no longer accurately describes what was built.
- **Pending/in_progress nodes**: Did this PR change APIs, types, or patterns that make a future node's description inaccurate?

For each stale description:

```bash
erk exec update-objective-node <objective_number> --node <node_id> --description "<corrected description>"
```

Keep descriptions concise (same style/length as existing nodes). Do node description updates *before* prose updates, since `update-objective-node` re-renders the comment table.
```

## Why This Works

- **No new tooling needed.** `erk exec update-objective-node --description` already handles YAML update + issue body write + comment table re-render.
- **Step 1 already provides all data.** The `roadmap.phases[].nodes[].description` fields are in the JSON output from Step 1, so the LLM has all descriptions in context.
- **Minimal instruction surface.** ~10 lines of new guidance, well within what the LLM can reliably follow.
- **Order before prose.** Node description updates re-render the comment table. Doing them before the prose update avoids any splice conflicts.

## Verification

1. Land a PR that has naming divergence from its objective node descriptions
2. Observe that the LLM calls `erk exec update-objective-node --description` for stale nodes
3. Verify the YAML roadmap and rendered comment table both reflect the updated descriptions
