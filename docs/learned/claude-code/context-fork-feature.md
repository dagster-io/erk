---
title: Context Fork Feature
last_audited: "2026-02-16 03:30 PT"
audit_result: clean
read_when:
  - "creating skills that need context isolation"
  - "creating commands that need context isolation"
  - "choosing between context: fork vs manual Task delegation"
  - "understanding when NOT to use context isolation"
tripwires:
  - action: "creating a skill or command with context: fork without explicit task instructions"
    warning: "Skills/commands with context: fork need actionable task prompts. Guidelines-only content returns empty output."
---

# Context Fork Feature

## The Design Decision

The `context: fork` frontmatter option (added in Claude Code 2.1.0) runs skills and commands in isolated subagent contexts. The skill/command content **becomes the entire prompt** for a fresh agent with no conversation history.

This is a declarative alternative to manual Task delegation. Why add it?

**Reusability**: Fetch-and-classify patterns (like PR comment analysis) were being duplicated across multiple commands as inline Task prompts. Extracting to a skill with `context: fork` eliminated duplication — now any command can invoke the skill.

**Maintenance**: When classification logic changed (e.g., adding complexity tiers), manual Task prompts in 5+ commands had to be updated. With `context: fork`, the logic lives in one skill file.

## When This Feature Makes Sense

Use `context: fork` when:

1. **Reusable pattern** — Multiple commands need the same fetch/classify operation
2. **Static logic** — Classification rules don't depend on runtime conversation context
3. **Context reduction** — Large responses (2,000+ tokens) would pollute parent context

Do NOT use when:

1. **Guidelines only** — If the content is "here's how to approach X" without explicit steps, the subagent will return empty/unhelpful output. Subagents execute tasks, not follow ambient guidelines.
2. **Dynamic prompts** — If you need to build prompts with runtime values from conversation, use manual Task delegation instead
3. **Needs conversation context** — If the skill must reference prior messages or user preferences

## The Empty Output Trap

**Most common mistake**: Treating forked skills like reference material.

WRONG (produces empty output):

```yaml
---
context: fork
---
# Python Coding Standards

Follow these conventions:
  - Use LBYL, never EAFP
  - Frozen dataclasses only
```

This fails because the subagent has no task. It reads guidelines but has nothing to _do_.

RIGHT:

```yaml
---
context: fork
---
# PR Feedback Classifier

Fetch PR comments and return structured JSON.

## Steps
1. Get branch and PR info via gh pr view
2. Fetch comments via erk exec commands
3. Classify each comment
4. Output JSON with thread IDs
```

The subagent has concrete steps to execute.

## Why Commands Support Frontmatter

Before Claude Code 2.1.0, only skills supported frontmatter. Commands were raw markdown with no metadata.

The extension made commands first-class: same frontmatter options as skills (including `context: fork`, `agent`, `argument-hint`). This eliminated the skill-vs-command distinction for most purposes.

**Implications:**

- Commands can now delegate to subagents without manual Task calls
- Batch operations (like scanning docs) can be command-driven
- No need to create a skill if the operation is single-purpose

<!-- Source: .claude/commands/local/audit-doc.md, frontmatter -->
<!-- Source: .claude/commands/local/audit-scan.md, parallel batch scoring -->

See `/local:audit-doc` and `/local:audit-scan` for commands using `context: fork` with `agent: general-purpose` for isolated analysis.

## Fork vs Manual Task: The Real Trade-Off

The comparison isn't about technical capability — both achieve context isolation. The choice is about **prompt ownership**.

| Approach        | Prompt Lives In             | When to Use                                               |
| --------------- | --------------------------- | --------------------------------------------------------- |
| `context: fork` | Skill/command file (static) | Reusable logic, fixed classification rules                |
| Manual Task     | Parent command (dynamic)    | Runtime-generated prompts, conversation-dependent context |

<!-- Source: .claude/commands/erk/learn.md, Agent 1-4 parallel launch with dynamic prompts -->

See `/erk:learn` for manual Task pattern. It builds prompts with session IDs and PR numbers extracted at runtime — impossible with static skill content.

## Agent Type Selection

The `agent` frontmatter field controls which subagent type runs the forked context:

- `general-purpose` — Full tool access (default)
- `Explore` — Read-only tools (Glob, Grep, Read, Bash)
- `Plan` — Planning-focused agent

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, frontmatter -->

See `pr-feedback-classifier` skill for `agent: general-purpose` usage. It needs Bash for erk exec commands and Write for output, which Explore doesn't provide.

## Token Savings Mechanism

**The insight**: Subagent context is disposable. When the Task completes, all intermediate data (verbose API responses, classification reasoning) disappears. Only the final output enters parent context.

For PR comment fetches:

- Direct fetch in parent: ~2,500 tokens (raw JSON persists)
- Forked skill: ~750 tokens (only summary + structured data returned)
- **Reduction: 65-70%**

See `docs/learned/architecture/task-context-isolation.md` for detailed pattern mechanics.

## Anti-Pattern: Prose Context Leakage

Using `context: fork` but returning verbose prose defeats the isolation.

WRONG:

```
Found 3 threads:

Thread PRRT_abc: "This needs to use LBYL pattern. The current code uses try/except which creates misleading traces because when the exception is raised it..."
[2,000 more tokens of quoted comment text]
```

The subagent copied verbose data into output — parent sees all of it.

RIGHT:

```
3 actionable threads, 12 informational skipped.

| # | Location | Issue | Complexity |
|---|----------|-------|------------|
| 1 | foo.py:42 | Use LBYL | local |

See JSON below for thread IDs.
```

Compact prose + structured JSON. Parent parses JSON for thread IDs but doesn't read verbose details.

## Argument Passing

Forked skills receive arguments via `$ARGUMENTS` variable. The subagent parses flags at runtime.

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, arguments section -->

See `pr-feedback-classifier` skill for `--pr <number>` and `--include-resolved` flag handling. Check `$ARGUMENTS` and conditionally pass flags to exec commands.

## Output Format: Double Delivery

Why return both prose AND JSON?

1. **Prose for users** — Human-readable summary they can scan
2. **JSON for parent** — Machine-parseable data for API calls (thread IDs, comment IDs)
3. **Single invocation** — No need for two separate fetches

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, output format section -->

See `pr-feedback-classifier` skill output schema. Note `thread_id` fields (for erk exec resolution) and `action_summary` (human-readable).

## Historical Context

Early PR addressing commands fetched comments inline. After 3-4 sessions, context windows filled with stale PR JSON from previous addresses. Manual Task delegation fixed context pollution but duplicated prompts across commands.

The `context: fork` feature (2.1.0) eliminated duplication — one skill, many callers. Commands gained frontmatter support (2.1.0) to enable single-purpose isolation without creating skills.

## Related Documentation

- [Task Context Isolation Pattern](../architecture/task-context-isolation.md) — Detailed pattern mechanics, token measurements
- [Agent Delegation](../planning/agent-delegation.md) — Full agent delegation patterns
