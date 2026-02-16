---
title: Reference Tripwires
read_when:
  - "working on reference code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from reference/*.md frontmatter -->

# Reference Tripwires

Rules triggered by matching actions in code.

**adding a changelog entry without a commit hash reference** → Read [Changelog Standards and Format](changelog-standards.md) first. All unreleased entries must include 9-character short hashes in parentheses. Hashes are stripped at release time by /local:changelog-release.

**adding a new roadmap status value** → Read [Objective Summary Format](objective-summary-format.md) first. Status inference lives in two places that must stay synchronized: the roadmap parser (roadmap.py in erk_shared/gateway/github/metadata/) and the agent prompt in objective-next-plan.md. Update both or the formats will diverge.

**adding a new workflow_dispatch workflow without run-name** → Read [GitHub Actions API Interaction Patterns](github-actions-api.md) first. Every erk workflow must use run-name with distinct_id for trigger_workflow discovery. Pattern: run-name: '<context>:${{ inputs.distinct_id }}'

**confusing `dangerous` with `allow_dangerous`** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. `dangerous` forces skip all prompts (automation). `allow_dangerous` lets users opt in (productivity). See the decision table in this doc.

**defining the same skill or command in multiple TOML sections** → Read [TOML File Handling](toml-handling.md) first. TOML duplicate key constraint: Each skill/command must have a single canonical destination. See bundled-artifacts.md for portability classification.

**modifying CHANGELOG.md directly instead of using /local:changelog-update** → Read [Changelog Standards and Format](changelog-standards.md) first. Always use /local:changelog-update to sync with commits. Manual edits bypass the categorization agent and marker system.

**passing a non-None value to with_overrides() when wanting to preserve config** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. None means 'keep config value'. Any non-None value (including False) is an active override. `allow_dangerous_override=dangerous_flag` when the flag is False will DISABLE the setting, not preserve it.

**querying individual workflow runs in a loop** → Read [GitHub Actions API Interaction Patterns](github-actions-api.md) first. Use get_workflow_runs_by_node_ids for batch queries (GraphQL O(1) vs REST O(N)). See the REST vs GraphQL decision table.

**referencing InteractiveClaudeConfig in new code** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. Renamed to InteractiveAgentConfig. The class is backend-agnostic (supports Claude and Codex). Config section also renamed: user-facing key is still 'interactive_claude' but attribute is 'interactive_agent'.

**triggering a workflow_dispatch without a distinct_id input** → Read [GitHub Actions API Interaction Patterns](github-actions-api.md) first. All erk workflows use distinct_id for reliable run correlation. Without it, trigger_workflow cannot find the run ID. See the run-name convention.

**using ClaudePermissionMode directly in new commands** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. New code should use PermissionMode ('safe', 'edits', 'plan', 'dangerous'). The Claude-specific modes are an internal mapping detail.

**writing implementation-focused changelog entries** → Read [Changelog Standards and Format](changelog-standards.md) first. Entries must describe user-visible behavior, not internal implementation. Ask: 'Does an erk user see different behavior?'
