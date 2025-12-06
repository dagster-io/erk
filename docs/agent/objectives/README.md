# Objectives

Objectives define desired states of the codebase that agents work toward incrementally.

## What is an Objective?

An objective is not a task list - it's a **declaration of a desired state**. The key insight:

- **Task list**: "Do X, then Y, then Z" (procedural, ordered)
- **Objective**: "The codebase should look like this" (declarative, state-based)

An agent can pick up an objective at any point, assess the current state, and propose incremental work to move closer to the goal.

## When to Use Objectives

Objectives work well for:

1. **Large-scale refactoring** - Migrating from pattern A to pattern B across many files
2. **Asymptotic goals** - "All code should follow X convention" (may never be 100% done)
3. **Incremental improvement** - Work that can be done in small chunks over time
4. **Continuous maintenance** - Objectives that recur as new code is added

## Objective Structure

Each objective lives in its own folder:

```
objectives/
  objective-name/
    README.md       # The objective itself (stable definition)
    work-log.md     # What's been done, when, by whom
    learnings.md    # Discoveries that inform future work
```

### README.md sections

- **Desired State** - What we want the codebase to look like
- **Rationale** - Why this matters (helps agents make judgment calls)
- **Examples** - Before/after showing the transformation
- **Scope** - What's in/out
- **How to Contribute** - Workflow for agents picking up work
- **Status** - Achievable vs aspirational, current progress

## Workflow

### For humans

1. Create objective folder with README defining desired state
2. Optionally seed work-log and learnings
3. Ask agent: "Make progress on [objective]"

### For agents

1. Read objective README
2. Check work-log for recent context
3. Check learnings for patterns discovered
4. Assess current state (run verification commands)
5. Propose and implement incremental work
6. Update work-log and learnings
7. Report what was done

## Current Objectives

| Objective | Status | Description |
|-----------|--------|-------------|
| [cli-ensure-error-handling](cli-ensure-error-handling/) | In Progress | Migrate CLI error handling to use Ensure class |

## Creating New Objectives

1. Create folder: `docs/agent/objectives/your-objective-name/`
2. Write README.md defining the desired state
3. Create empty work-log.md and learnings.md
4. Add entry to the table above
