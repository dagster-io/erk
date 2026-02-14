---
title: Reference Tripwires
read_when:
  - "working on reference code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from reference/*.md frontmatter -->

# Reference Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding a changelog entry without a commit hash reference** → Read [Changelog Standards and Format](changelog-standards.md) first. All unreleased entries must include 9-character short hashes in parentheses. Hashes are stripped at release time by /local:changelog-release.

**CRITICAL: Before adding a new roadmap status value** → Read [Objective Summary Format](objective-summary-format.md) first. Status inference lives in two places that must stay synchronized: the roadmap parser (objective_roadmap_shared.py) and the agent prompt in objective-next-plan.md. Update both or the formats will diverge.

**CRITICAL: Before adding a new workflow_dispatch workflow without run-name** → Read [GitHub Actions API Interaction Patterns](github-actions-api.md) first. Every erk workflow must use run-name with distinct_id for trigger_workflow discovery. Pattern: run-name: '<context>:${{ inputs.distinct_id }}'

**CRITICAL: Before adding new fields to the roadmap schema without updating validate_roadmap_frontmatter()** → Read [Objective Roadmap Schema Reference](objective-roadmap-schema.md) first. New fields must be validated in validate_roadmap_frontmatter() in objective_roadmap_frontmatter.py. Extra fields are preserved but unknown required fields will cause validation failures.

**CRITICAL: Before confusing `dangerous` with `allow_dangerous`** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. `dangerous` forces skip all prompts (automation). `allow_dangerous` lets users opt in (productivity). See the decision table in this doc.

**CRITICAL: Before defining the same skill or command in multiple TOML sections** → Read [TOML File Handling](toml-handling.md) first. TOML duplicate key constraint: Each skill/command must have a single canonical destination. See bundled-artifacts.md for portability classification.

**CRITICAL: Before modifying CHANGELOG.md directly instead of using /local:changelog-update** → Read [Changelog Standards and Format](changelog-standards.md) first. Always use /local:changelog-update to sync with commits. Manual edits bypass the categorization agent and marker system.

**CRITICAL: Before passing a non-None value to with_overrides() when wanting to preserve config** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. None means 'keep config value'. Any non-None value (including False) is an active override. `allow_dangerous_override=dangerous_flag` when the flag is False will DISABLE the setting, not preserve it.

**CRITICAL: Before querying individual workflow runs in a loop** → Read [GitHub Actions API Interaction Patterns](github-actions-api.md) first. Use get_workflow_runs_by_node_ids for batch queries (GraphQL O(1) vs REST O(N)). See the REST vs GraphQL decision table.

**CRITICAL: Before referencing InteractiveClaudeConfig in new code** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. Renamed to InteractiveAgentConfig. The class is backend-agnostic (supports Claude and Codex). Config section also renamed: user-facing key is still 'interactive_claude' but attribute is 'interactive_agent'.

**CRITICAL: Before triggering a workflow_dispatch without a distinct_id input** → Read [GitHub Actions API Interaction Patterns](github-actions-api.md) first. All erk workflows use distinct_id for reliable run correlation. Without it, trigger_workflow cannot find the run ID. See the run-name convention.

**CRITICAL: Before using ClaudePermissionMode directly in new commands** → Read [Interactive Agent Configuration](interactive-claude-config.md) first. New code should use PermissionMode ('safe', 'edits', 'plan', 'dangerous'). The Claude-specific modes are an internal mapping detail.

**CRITICAL: Before writing implementation-focused changelog entries** → Read [Changelog Standards and Format](changelog-standards.md) first. Entries must describe user-visible behavior, not internal implementation. Ask: 'Does an erk user see different behavior?'
