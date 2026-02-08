<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Planning Documentation

- **[agent-delegation.md](agent-delegation.md)** — delegating to agents from commands, implementing command-agent pattern, workflow orchestration
- **[agent-orchestration-safety.md](agent-orchestration-safety.md)** — passing data between agents via files or inline output, designing multi-agent workflows with parallel and sequential tiers, orchestrating subagents that produce markdown, XML, or other large outputs
- **[agent-orchestration.md](agent-orchestration.md)** — designing agent workflows with parallel and sequential tiers, choosing between parallel and sequential agent execution, adding or modifying agents in the learn pipeline, deciding which model tier to assign an agent
- **[complete-inventory-protocol.md](complete-inventory-protocol.md)** — estimating effort or remaining work for a plan or PR, closing a plan issue as complete, creating a consolidation plan from multiple PRs
- **[consolidation-labels.md](consolidation-labels.md)** — consolidating multiple learn plans, working with erk-consolidated label, preventing re-consolidation of issues, modifying /local:replan-learn-plans or /erk:replan consolidation behavior
- **[context-preservation-in-replan.md](context-preservation-in-replan.md)** — implementing or modifying replan workflow steps, debugging why a replanned issue produced a sparse plan, adding new plan-creation workflows that use EnterPlanMode
- **[context-preservation-patterns.md](context-preservation-patterns.md)** — writing implementation plans (any workflow), reviewing plan content before saving to GitHub, creating consolidated plans from multiple sources, debugging why an implementing agent had to re-investigate
- **[cross-artifact-analysis.md](cross-artifact-analysis.md)** — detecting PR and plan relationships, assessing if work supersedes a plan, analyzing overlap between artifacts
- **[cross-repo-plans.md](cross-repo-plans.md)** — setting up plans in a separate repository, configuring [plans] repo in config.toml, understanding cross-repo issue closing syntax
- **[gateway-consolidation-checklist.md](gateway-consolidation-checklist.md)** — moving gateways to gateway/ directory, consolidating gateway packages, performing systematic refactoring
- **[learn-pipeline-workflow.md](learn-pipeline-workflow.md)** — Understanding the complete learn pipeline, Working with async learn workflow, Debugging learn plan execution, Implementing learn plan orchestration
- **[learn-plan-metadata-fields.md](learn-plan-metadata-fields.md)** — working with learn plan metadata, troubleshooting null learn_status or learn_plan_issue, transforming Plan objects in pipelines, understanding created_from_workflow_run_url field, adding workflow run backlinks to plans
- **[learn-plan-validation.md](learn-plan-validation.md)** — creating or modifying erk-learn plans, working on the learn workflow pipeline, debugging learn-on-learn cycle errors
- **[learn-vs-implementation-plans.md](learn-vs-implementation-plans.md)** — choosing between plan types, creating erk-learn plans, understanding how learn plans relate to implementation plans, debugging learn plan base branch selection
- **[learn-without-pr-context.md](learn-without-pr-context.md)** — debugging learn workflow failures where PR data is missing, implementing new learn pipeline steps that consume PR context, understanding why learn output lacks review feedback
- **[learn-workflow.md](learn-workflow.md)** — using /erk:learn skill, understanding learn status tracking, auto-updating parent plans when learn plans land
- **[lifecycle.md](lifecycle.md)** — creating a plan, closing a plan, understanding plan states
- **[metadata-block-fallback.md](metadata-block-fallback.md)** — extracting plan content from GitHub issue comments, debugging 'no plan content found' errors in replan or plan-implement, working with older erk-plan issues that lack metadata blocks
- **[metadata-field-workflow.md](metadata-field-workflow.md)** — adding a new field to plan-header metadata, extending plan issue schema, coordinating metadata changes across files
- **[no-changes-handling.md](no-changes-handling.md)** — implementing erk-impl workflow, debugging no-changes scenarios, understanding erk-impl error handling
- **[plan-lookup-strategy.md](plan-lookup-strategy.md)** — debugging plan lookup issues, understanding plan file discovery, troubleshooting wrong plan saved
- **[plan-schema.md](plan-schema.md)** — understanding plan issue structure, debugging plan validation errors, working with plan-header or plan-body blocks
- **[pr-analysis-pattern.md](pr-analysis-pattern.md)** — analyzing PR changes for documentation, building workflows that inspect PRs
- **[pr-discovery.md](pr-discovery.md)** — finding the PR associated with an erk plan issue, debugging why get-pr-for-plan returns no-branch-in-plan, understanding how erk learn finds PRs, working with plan-header branch_name field
- **[pr-review-workflow.md](pr-review-workflow.md)** — creating or managing plan review PRs, addressing feedback on plan content via PR comments, understanding how review PRs relate to implementation PRs, closing or cleaning up plan review PRs
- **[pr-submission-patterns.md](pr-submission-patterns.md)** — creating or updating PRs programmatically in erk, debugging why a duplicate PR or issue was created, fixing erk pr check validation failures, understanding the PR number vs issue number distinction
- **[reliability-patterns.md](reliability-patterns.md)** — deciding whether an operation should be agent-driven or workflow-native, designing multi-layer resilience for critical automated operations, ordering git operations that mix cleanup with reset in CI workflows
- **[remote-implementation-idempotency.md](remote-implementation-idempotency.md)** — implementing remote plan execution, debugging branch creation in remote workflows, working with worktree reuse patterns
- **[scratch-storage.md](scratch-storage.md)** — writing temp files for AI workflows, passing files between processes, understanding scratch directory location
- **[session-deduplication.md](session-deduplication.md)** — understanding duplicate plan prevention, working with exit-plan-mode hook, debugging duplicate issue creation
- **[session-preprocessing.md](session-preprocessing.md)** — preprocessing sessions for learn workflow, understanding token budget for session analysis, working with session XML format
- **[sub-agent-context-limitations.md](sub-agent-context-limitations.md)** — debugging impl-signal failures, working with CLAUDE_SESSION_ID, delegating to Task tool sub-agents, implementing plan-save workflow
- **[submit-branch-reuse.md](submit-branch-reuse.md)** — implementing erk plan submit, handling duplicate branches, resubmitting a plan issue
- **[token-optimization-patterns.md](token-optimization-patterns.md)** — designing multi-agent workflows, handling large data payloads in agent orchestration, experiencing context bloat from fetching multiple documents, building consolidation or aggregation commands
- **[tripwire-promotion-workflow.md](tripwire-promotion-workflow.md)** — implementing tripwire candidate extraction, promoting tripwire candidates to frontmatter, understanding the learn-to-tripwire pipeline
- **[tripwire-worthiness-criteria.md](tripwire-worthiness-criteria.md)** — evaluating whether an insight deserves tripwire status, reviewing [TRIPWIRE-CANDIDATE] items from learn workflow, understanding what makes something tripwire-worthy
- **[workflow-markers.md](workflow-markers.md)** — building multi-step workflows that need state persistence, using erk exec marker commands, implementing objective-to-plan workflows
- **[workflow.md](workflow.md)** — using .impl/ folders, understanding plan file structure, implementing plans
- **[worktree-cleanup.md](worktree-cleanup.md)** — implementing plans with .worker-impl/ folders, understanding when to clean up .worker-impl/, debugging plan implementation workflows
