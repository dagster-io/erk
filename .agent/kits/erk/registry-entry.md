### erk (v0.3.1)

**Purpose**: Erk implementation workflow commands for creating worktrees from plans (.PLAN.md) and executing implementation. Includes commands for plan creation, execution, and quick access.

**Artifacts**:

- command: commands/erk/plan-implement.md, commands/erk/merge-conflicts-fix.md, commands/erk/submit-plan.md, commands/erk/auto-restack.md
- agent: agents/erk/issue-wt-creator.md, agents/erk/plan-extractor.md
- doc: docs/erk/EXAMPLES.md, docs/erk/includes/create-github-issue.md, docs/erk/includes/enrichment-process.md, docs/erk/includes/planning/next-steps-output.md, docs/erk/includes/session-file-location.md, docs/erk/includes/success-output-format.md, docs/erk/includes/validate-git-repository.md, docs/erk/includes/validate-github-cli.md, docs/erk/includes/validate-plan-structure.md

**Usage**:

- Use Task tool with subagent_type="erk"
- Run `/erk` command
