<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Planning Documentation

- **[agent-delegation.md](agent-delegation.md)** — delegating to agents from commands, implementing command-agent pattern, workflow orchestration
- **[consolidation-labels.md](consolidation-labels.md)** — consolidating multiple learn plans, working with erk-consolidated label, preventing re-consolidation of issues, running /local:replan-learn-plans
- **[cross-artifact-analysis.md](cross-artifact-analysis.md)** — detecting PR and plan relationships, assessing if work supersedes a plan, analyzing overlap between artifacts
- **[cross-repo-plans.md](cross-repo-plans.md)** — setting up plans in a separate repository, configuring [plans] repo in config.toml, understanding cross-repo issue closing syntax
- **[learn-plan-metadata-fields.md](learn-plan-metadata-fields.md)** — working with learn plan metadata, troubleshooting null learn_status or learn_plan_issue, transforming Plan objects in pipelines, understanding created_from_workflow_run_url field, adding workflow run backlinks to plans
- **[learn-workflow.md](learn-workflow.md)** — using /erk:learn skill, understanding learn status tracking, auto-updating parent plans when learn plans land
- **[lifecycle.md](lifecycle.md)** — creating a plan, closing a plan, understanding plan states
- **[metadata-field-workflow.md](metadata-field-workflow.md)** — adding a new field to plan-header metadata, extending plan issue schema, coordinating metadata changes across files
- **[no-changes-handling.md](no-changes-handling.md)** — implementing erk-impl workflow, debugging no-changes scenarios, understanding erk-impl error handling
- **[plan-lookup-strategy.md](plan-lookup-strategy.md)** — debugging plan lookup issues, understanding plan file discovery, troubleshooting wrong plan saved
- **[plan-schema.md](plan-schema.md)** — understanding plan issue structure, debugging plan validation errors, working with plan-header or plan-body blocks
- **[pr-analysis-pattern.md](pr-analysis-pattern.md)** — analyzing PR changes for documentation, building workflows that inspect PRs
- **[pr-submission-patterns.md](pr-submission-patterns.md)** — creating PRs programmatically, implementing idempotent PR submission, handling retry logic for PR operations
- **[reliability-patterns.md](reliability-patterns.md)** — designing cleanup operations in workflows, choosing between agent vs workflow-native operations, implementing multi-layer failure resilience
- **[remote-implementation-idempotency.md](remote-implementation-idempotency.md)** — implementing remote plan execution, debugging branch creation in remote workflows, working with worktree reuse patterns
- **[roadmap-updates.md](roadmap-updates.md)** — updating objective roadmap tables, working with update_roadmap_with_plan function, adding plan references to roadmap steps, understanding PR column format in objectives
- **[scratch-storage.md](scratch-storage.md)** — writing temp files for AI workflows, passing files between processes, understanding scratch directory location
- **[session-deduplication.md](session-deduplication.md)** — understanding duplicate plan prevention, working with exit-plan-mode hook, debugging duplicate issue creation
- **[submit-branch-reuse.md](submit-branch-reuse.md)** — implementing erk plan submit, handling duplicate branches, resubmitting a plan issue
- **[tripwire-promotion-workflow.md](tripwire-promotion-workflow.md)** — implementing tripwire candidate extraction, promoting tripwire candidates to frontmatter, understanding the learn-to-tripwire pipeline
- **[tripwire-worthiness-criteria.md](tripwire-worthiness-criteria.md)** — evaluating whether an insight deserves tripwire status, reviewing [TRIPWIRE-CANDIDATE] items from learn workflow, understanding what makes something tripwire-worthy
- **[workflow-markers.md](workflow-markers.md)** — building multi-step workflows that need state persistence, using erk exec marker commands, implementing objective-to-plan workflows
- **[workflow.md](workflow.md)** — using .impl/ folders, understanding plan file structure, implementing plans
