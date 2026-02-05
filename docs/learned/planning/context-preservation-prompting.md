---
title: Context Preservation Prompting Patterns
last_audited: "2026-02-05 16:55 PT"
audit_result: edited
read_when:
  - "writing slash commands that create plans"
  - "implementing replan workflows"
  - "designing consolidation prompts"
---

# Context Preservation Prompting Patterns

Specific prompt structures that reliably elicit investigation context in plan creation.

## Canonical Implementation

The canonical implementation of context preservation prompting lives in `.claude/commands/erk/replan.md`:

- **Step 6a** (lines 224-238): Gather Investigation Context before Plan Mode
- **Step 6b** (lines 239-264): Enter Plan Mode with explicit requirements for incorporating findings

Read those steps directly for the template and examples. The sibling docs provide additional context:

- [Context Preservation in Replan](context-preservation-in-replan.md) — Why Steps 6a-6b exist, the sparse plan problem, and detailed examples
- [Context Preservation Patterns](context-preservation-patterns.md) — Anti-patterns vs. correct patterns with side-by-side comparisons
- [Investigation Findings Checklist](../checklists/investigation-findings.md) — Pre-plan-mode verification checklist

---

## Adaptation Guidelines

### For Other Plan Creation Workflows

When creating new workflows that generate plans, apply the same two-phase structure from `/erk:replan`:

1. **Always add a gathering step** before `EnterPlanMode` — collect file paths, line numbers, evidence, and discoveries explicitly
2. **Use the CRITICAL tag** on mandatory requirements (agents frequently skip gathering steps without it)
3. **Provide anti-pattern and correct pattern examples** — show what sparse plans look like vs. comprehensive ones
4. **List context types to gather** — status, discoveries, corrections, and codebase evidence (4 categories minimum)

### For Non-Replan Workflows

Even for fresh plans (not replanning), context preservation applies. Before entering Plan Mode, gather:

1. **Codebase discoveries**: Actual file names, function signatures, class definitions
2. **Architecture insights**: How components interact, data flow patterns
3. **Constraints found**: API limits, type requirements, validation rules
4. **Verification approach**: How to confirm each step is complete

Plan steps must reference specific files with line numbers, not generic descriptions.

### Interviewing Within Plan Mode

When requirements are ambiguous or underspecified, use `/local:interview` to gather context before planning.

**Pattern: Interview then Gather then Plan**

1. **Clarify requirements**: Launch `/local:interview <topic>` to ask clarifying questions and search codebase
2. **Resume with context**: After interview completes, the conversation resumes with gathered context in history
3. **Gather and plan**: Follow the standard context preservation pattern (Steps 6a-6b) incorporating interview findings

The `/local:interview` command uses `allowed-tools: AskUserQuestion, Read, Glob, Grep` frontmatter to enforce read-only behavior, making it safe for use in plan mode. See [Tool Restriction Safety](../commands/tool-restriction-safety.md) for the pattern.

---

## Related Documentation

- [Context Preservation in Replan](context-preservation-in-replan.md) - Why Steps 6a-6b exist
- [Context Preservation Patterns](context-preservation-patterns.md) - Anti-patterns vs. correct patterns
- [Investigation Findings Checklist](../checklists/investigation-findings.md) - Verification checklist
- [Replan Command](../../../.claude/commands/erk/replan.md) - Reference implementation
