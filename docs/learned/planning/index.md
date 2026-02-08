<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Planning Documentation

- **[agent-delegation.md](agent-delegation.md)** — delegating to agents from commands, implementing command-agent pattern, workflow orchestration
- **[agent-orchestration-safety.md](agent-orchestration-safety.md)** — passing data between agents via files or inline output, designing multi-agent workflows with parallel and sequential tiers, orchestrating subagents that produce markdown, XML, or other large outputs
- **[agent-orchestration.md](agent-orchestration.md)** — designing agent workflows with parallel and sequential tiers, choosing between parallel and sequential agent execution, adding or modifying agents in the learn pipeline, deciding which model tier to assign an agent
- **[async-learn-local-preprocessing.md](async-learn-local-preprocessing.md)** — modifying trigger-async-learn orchestration, debugging why learn materials are missing or malformed in CI, understanding the local-to-gist-to-codespace data flow
- **[branch-name-inference.md](branch-name-inference.md)** — debugging missing branch_name in plan issues, implementing PR lookup from plan issues, modifying branch creation or naming conventions
- **[complete-inventory-protocol.md](complete-inventory-protocol.md)** — estimating effort or remaining work for a plan or PR, closing a plan issue as complete, creating a consolidation plan from multiple PRs
- **[consolidation-labels.md](consolidation-labels.md)** — consolidating multiple learn plans, working with erk-consolidated label, preventing re-consolidation of issues, modifying /local:replan-learn-plans or /erk:replan consolidation behavior
- **[context-preservation-in-replan.md](context-preservation-in-replan.md)** — implementing or modifying replan workflow steps, debugging why a replanned issue produced a sparse plan, adding new plan-creation workflows that use EnterPlanMode
- **[context-preservation-patterns.md](context-preservation-patterns.md)** — writing implementation plans (any workflow), reviewing plan content before saving to GitHub, creating consolidated plans from multiple sources, debugging why an implementing agent had to re-investigate
- **[context-preservation-prompting.md](context-preservation-prompting.md)** — writing slash commands that create plans, designing any workflow that calls EnterPlanMode, understanding why plans lose investigation context
- **[cross-artifact-analysis.md](cross-artifact-analysis.md)** — detecting PR and plan relationships, assessing if work supersedes a plan, analyzing overlap between artifacts
- **[cross-repo-plans.md](cross-repo-plans.md)** — setting up plans in a separate repository, configuring [plans] repo in config.toml, understanding cross-repo issue closing syntax
- **[debugging-patterns.md](debugging-patterns.md)** — Debugging validation failures after an initial fix attempt fails, Encountering errors where the required format is unclear from the error message alone, Deciding whether to guess at another fix or read the validator source
- **[gateway-consolidation-checklist.md](gateway-consolidation-checklist.md)** — moving gateways to gateway/ directory, consolidating gateway packages, performing systematic refactoring
- **[learn-pipeline-workflow.md](learn-pipeline-workflow.md)** — Understanding the complete learn pipeline, Working with async learn workflow, Debugging learn plan execution, Implementing learn plan orchestration
- **[learn-plan-metadata-fields.md](learn-plan-metadata-fields.md)** — working with learn plan metadata, troubleshooting null learn_status or learn_plan_issue, transforming Plan objects in pipelines, understanding created_from_workflow_run_url field, adding workflow run backlinks to plans
- **[learn-plan-validation.md](learn-plan-validation.md)** — creating erk-learn plans, preventing learn plan cycles, validating learn workflow
- **[learn-vs-implementation-plans.md](learn-vs-implementation-plans.md)** — choosing between plan types, creating erk-learn plans, understanding plan workflows
- **[learn-without-pr-context.md](learn-without-pr-context.md)** — debugging learn workflow failures, implementing plans without creating PRs, understanding workflow variance in learn
- **[learn-workflow.md](learn-workflow.md)** — using /erk:learn skill, understanding learn status tracking, auto-updating parent plans when learn plans land
- **[lifecycle.md](lifecycle.md)** — creating a plan, closing a plan, understanding plan states
- **[metadata-block-fallback.md](metadata-block-fallback.md)** — fetching plan content from GitHub issues, debugging 'no plan content found' errors, working with older erk-plan issues, implementing plan content extraction
- **[metadata-field-workflow.md](metadata-field-workflow.md)** — adding a new field to plan-header metadata, extending plan issue schema, coordinating metadata changes across files
- **[no-changes-handling.md](no-changes-handling.md)** — implementing erk-impl workflow, debugging no-changes scenarios, understanding erk-impl error handling
- **[plan-lookup-strategy.md](plan-lookup-strategy.md)** — debugging plan lookup issues, understanding plan file discovery, troubleshooting wrong plan saved
- **[plan-schema.md](plan-schema.md)** — understanding plan issue structure, debugging plan validation errors, working with plan-header or plan-body blocks
- **[pr-analysis-pattern.md](pr-analysis-pattern.md)** — analyzing PR changes for documentation, building workflows that inspect PRs
- **[pr-discovery.md](pr-discovery.md)** — implementing erk learn workflow, discovering PRs when branch_name is missing, debugging PR discovery failures, working with session metadata
- **[pr-review-workflow.md](pr-review-workflow.md)** — Reviewing plans collaboratively before implementation
- **[pr-submission-patterns.md](pr-submission-patterns.md)** — creating PRs programmatically, implementing idempotent PR submission, handling retry logic for PR operations
- **[reliability-patterns.md](reliability-patterns.md)** — designing cleanup operations in workflows, choosing between agent vs workflow-native operations, implementing multi-layer failure resilience
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
