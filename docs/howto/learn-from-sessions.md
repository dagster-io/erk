# Learn from Sessions

Extract insights from implementation sessions to improve future agent efficiency.

## Overview

When Claude Code implements a plan, the session contains valuable learnings: patterns discovered, errors resolved, external resources fetched, and design decisions made. The `/erk:learn` command analyzes these sessions and creates a documentation plan to capture insights before they're lost.

Documentation created by learn is a "token cache" for future agents. Instead of burning tokens rediscovering the same patterns, quirks, and gotchas, future agents can load the documented knowledge directly.

## When to Use Learn

Run learn in these situations:

- **After landing a PR** - `erk land` prompts you if learn hasn't been run
- **Before abandoning a worktree** - Capture insights before context is lost
- **After discovering non-obvious patterns** - Document what surprised you
- **After resolving tricky errors** - Save the solution for next time

Learn documentation goes in `docs/learned/` and is consumed by AI agents, not human users. For user-facing documentation, use the standard `docs/` directories.

## Run Learn on a Plan

### Step 1: Invoke the Command

From any worktree with a plan-linked branch:

```
/erk:learn
```

Or specify an issue number explicitly:

```
/erk:learn 4655
```

You can also run learn from the CLI:

```bash
erk learn
erk learn 4655  # With explicit issue number
```

### Step 2: Review Findings

Claude analyzes the planning and implementation sessions, then presents:

- **Summary of insights** with source attribution
- **Proposed documentation items** with locations and actions
- **Questions** about what to include or exclude

Review the findings and provide feedback. Add insights Claude missed, or remove items that aren't valuable.

### Step 3: Approve the Documentation Plan

Once you're satisfied with the findings, Claude creates a GitHub issue containing:

- Rich context section with key files and patterns
- Link to a gist with the raw session materials
- Documentation items with location, action (create/update), and draft content

### Step 4: Implement Later

The documentation plan is now a standard erk plan issue. Implement it when ready:

```bash
erk implement <issue-number>
```

## What Learn Produces

A GitHub issue labeled `erk-learn` containing:

| Section                 | Contents                                          |
| ----------------------- | ------------------------------------------------- |
| **Context**             | Key files, patterns found, relevant existing docs |
| **Raw Materials**       | Gist link to preprocessed session files           |
| **Documentation Items** | Location, action, draft content, and source       |

The raw materials gist preserves the session context so the implementing agent can reference it when writing documentation.

## Skip the Learn Prompt

If you don't want to be prompted about learn when landing PRs:

**Per-PR:** Use the force flag to skip the prompt:

```bash
erk land -f
```

**Globally:** Disable the prompt in erk configuration:

```bash
erk config set prompt_learn_on_land false
```

## See Also

- [Use the Local Workflow](local-workflow.md) - The standard development cycle
- [The Workflow](../topics/the-workflow.md) - Conceptual overview of erk's workflow
- [Agent Documentation Index](../../docs/learned/index.md) - Where learn documentation lives
