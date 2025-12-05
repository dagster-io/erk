---
title: PR Workflow Integration Pattern
read_when:
  - "adding validation steps to PR workflows"
  - "integrating new checks into PR submission"
  - "updating PR workflow commands"
---

# PR Workflow Integration Pattern

When creating a new validation or hook that should run during PR submission, integrate it into all relevant workflows.

## Workflows to Update

When adding PR validation or hooks, update these workflows:

1. **`/gt:pr-submit`** - Graphite-based PR submission
   - Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-submit.md`
   - Add step after PR finalization, before results reporting

2. **`/gt:pr-update`** - Graphite PR update
   - Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/commands/gt/pr-update.md`
   - Add step after update workflow completes

3. **`/git:pr-push`** - Standard git PR creation
   - Location: `.claude/commands/git/pr-push.md`
   - Add step after `gh pr create`, before results reporting

4. **`/erk:plan-implement`** - Implementation workflow
   - Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-implement.md`
   - Add step after PR creation (only for worker-impl flows)

## Integration Pattern

Use this template when adding a validation step:

```markdown
### Step N: Validate PR Rules

Run the PR check command to validate the PR:

\`\`\`bash
erk pr check
\`\`\`

This validates:

- [List what the check validates]

If any checks fail, display the output and warn the user.
```

### Step Numbering

When adding new steps:

1. Insert the step in the logical position in the workflow
2. Renumber all subsequent steps to maintain whole numbers
3. Never use fractional steps (e.g., 1.5, 2.5)

See [Slash Command Conventions](../commands/slash-command-conventions.md) for details.

## Non-Blocking Behavior

PR validation steps should be non-blocking by default:

- Display warnings if checks fail
- Continue to next step (results reporting)
- Let user decide whether to fix issues

This approach:

- Allows workflows to complete even with validation warnings
- Provides visibility into issues
- Respects user agency to address issues on their timeline
- Prevents blocking automated workflows

## Example: Adding erk pr check

The `erk pr check` command was integrated using this pattern:

**Location in workflow**: After PR creation/update, before results reporting

**Integration code**:

```markdown
### Step 16: Validate PR Rules

After creating/updating the PR, run the PR check command to validate:

\`\`\`bash
erk pr check
\`\`\`

This validates:

- Issue closing reference (Closes #N) is present when `.impl/issue.json` exists
- PR body contains the standard checkout footer

If any checks fail, display the output and warn the user.
```

**Added to**: All four PR workflows listed above

## Related Topics

- [Slash Command Conventions](../commands/slash-command-conventions.md) - Step numbering rules
- [PR Commands](../cli/pr-commands.md) - The `erk pr check` command
- [Command Organization](../cli/command-organization.md) - How commands are structured
