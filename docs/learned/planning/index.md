<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Planning Documentation

- **[agent-delegation.md](agent-delegation.md)** — delegating to agents from commands, implementing command-agent pattern, workflow orchestration
- **[consolidation-labels.md](consolidation-labels.md)** — consolidating multiple learn plans, working with erk-consolidated label, preventing re-consolidation of issues, running /local:replan-learn-plans
- **[context-preservation-in-replan.md](context-preservation-in-replan.md)** — implementing replan workflow, creating consolidated plans, understanding sparse plan prevention
- **[context-preservation-patterns.md](context-preservation-patterns.md)** — writing implementation plans, creating consolidated plans, avoiding sparse plan content
- **[context-preservation-prompting.md](context-preservation-prompting.md)** — writing slash commands that create plans, implementing replan workflows, designing consolidation prompts
- **[cross-artifact-analysis.md](cross-artifact-analysis.md)** — detecting PR and plan relationships, assessing if work supersedes a plan, analyzing overlap between artifacts
- **[cross-repo-plans.md](cross-repo-plans.md)** — setting up plans in a separate repository, configuring [plans] repo in config.toml, understanding cross-repo issue closing syntax
- **[gateway-consolidation-checklist.md](gateway-consolidation-checklist.md)** — moving gateways to gateway/ directory, consolidating gateway packages, performing systematic refactoring
- **[learn-plan-metadata-fields.md](learn-plan-metadata-fields.md)** — working with learn plan metadata, troubleshooting null learn_status or learn_plan_issue, transforming Plan objects in pipelines, understanding created_from_workflow_run_url field, adding workflow run backlinks to plans
- **[learn-plan-validation.md](learn-plan-validation.md)** — creating erk-learn plans, preventing learn plan cycles, validating learn workflow
- **[learn-vs-implementation-plans.md](learn-vs-implementation-plans.md)** — choosing between plan types, creating erk-learn plans, understanding plan workflows
- **[learn-workflow.md](learn-workflow.md)** — using /erk:learn skill, understanding learn status tracking, auto-updating parent plans when learn plans land
- **[lifecycle.md](lifecycle.md)** — creating a plan, closing a plan, understanding plan states
- **[metadata-field-workflow.md](metadata-field-workflow.md)** — adding a new field to plan-header metadata, extending plan issue schema, coordinating metadata changes across files
- **[no-changes-handling.md](no-changes-handling.md)** — implementing erk-impl workflow, debugging no-changes scenarios, understanding erk-impl error handling
- **[plan-lookup-strategy.md](plan-lookup-strategy.md)** — debugging plan lookup issues, understanding plan file discovery, troubleshooting wrong plan saved
- **[plan-schema.md](plan-schema.md)** — understanding plan issue structure, debugging plan validation errors, working with plan-header or plan-body blocks
- **[pr-analysis-pattern.md](pr-analysis-pattern.md)** — analyzing PR changes for documentation, building workflows that inspect PRs
- **[pr-discovery.md](pr-discovery.md)** — implementing erk learn workflow, discovering PRs when branch_name is missing, debugging PR discovery failures, working with session metadata
- **[pr-review-workflow.md](pr-review-workflow.md)** — creating a PR for plan review, setting up asynchronous plan review, understanding review_pr metadata field
- **[pr-submission-patterns.md](pr-submission-patterns.md)** — creating PRs programmatically, implementing idempotent PR submission, handling retry logic for PR operations
- **[reliability-patterns.md](reliability-patterns.md)** — designing cleanup operations in workflows, choosing between agent vs workflow-native operations, implementing multi-layer failure resilience
- **[remote-implementation-idempotency.md](remote-implementation-idempotency.md)** — implementing remote plan execution, debugging branch creation in remote workflows, working with worktree reuse patterns
- **[scratch-storage.md](scratch-storage.md)** — writing temp files for AI workflows, passing files between processes, understanding scratch directory location
- **[session-deduplication.md](session-deduplication.md)** — understanding duplicate plan prevention, working with exit-plan-mode hook, debugging duplicate issue creation
- **[submit-branch-reuse.md](submit-branch-reuse.md)** — implementing erk plan submit, handling duplicate branches, resubmitting a plan issue
- **[tripwire-promotion-workflow.md](tripwire-promotion-workflow.md)** — implementing tripwire candidate extraction, promoting tripwire candidates to frontmatter, understanding the learn-to-tripwire pipeline
- **[tripwire-worthiness-criteria.md](tripwire-worthiness-criteria.md)** — evaluating whether an insight deserves tripwire status, reviewing [TRIPWIRE-CANDIDATE] items from learn workflow, understanding what makes something tripwire-worthy
- **[workflow-markers.md](workflow-markers.md)** — building multi-step workflows that need state persistence, using erk exec marker commands, implementing objective-to-plan workflows
- **[workflow.md](workflow.md)** — using .impl/ folders, understanding plan file structure, implementing plans
