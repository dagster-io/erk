### erk (v0.2.7)

**Purpose**: Erk implementation workflow commands for creating worktrees from plans (.PLAN.md) and executing implementation. Includes commands for plan creation, execution, and quick access.

**Artifacts**:

- command: commands/erk/plan-implement.md, commands/erk/merge-conflicts-fix.md, commands/erk/plan-submit.md, commands/erk/auto-restack.md, commands/erk/create-extraction-plan.md, commands/erk/save-plan.md, commands/erk/pr-address.md, commands/erk/pr-submit.md
- agent: agents/erk/issue-wt-creator.md
- doc: docs/erk/EXAMPLES.md, docs/erk/includes/conflict-resolution.md, docs/erk/includes/create-github-issue.md, docs/erk/includes/extract-docs-analysis-shared.md, docs/erk/includes/extract-plan-workflow-shared.md, docs/erk/includes/planning/extract-plan-from-session.md, docs/erk/includes/planning/next-steps-output.md, docs/erk/includes/session-file-location.md, docs/erk/includes/success-output-format.md, docs/erk/includes/validate-git-repository.md, docs/erk/includes/validate-github-cli.md, docs/erk/includes/validate-plan-structure.md

**Usage**:

- Use Task tool with subagent_type="erk"
- Run `/erk` command
