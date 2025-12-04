---
title: Behavioral Triggers
read_when:
  - "adding documentation routing rules"
  - "making documentation more discoverable"
  - "preventing common agent mistakes"
---

# Behavioral Triggers

Behavioral triggers are detection rules that route agents to documentation when specific action patterns are detected.

## The Problem

Documentation can exist and be indexed, but agents may still make mistakes because:

1. The agent doesn't know to look for the documentation
2. The action happens before the agent thinks to check docs
3. The "read when" conditions in docs aren't triggered by the specific action

## The Pattern

Add triggers to AGENTS.md that detect **actions about to happen** and route to the relevant documentation:

```markdown
**CRITICAL: Before [action pattern]** → Read [doc-path] first. [Brief explanation].
```

### Examples

| Action Pattern                      | Trigger                          | Routes To              |
| ----------------------------------- | -------------------------------- | ---------------------- |
| Writing to `/tmp/`                  | Before writing temp files        | scratch-storage.md     |
| Using `try/except` for control flow | Before adding exception handling | dignified-python skill |
| Creating a Protocol                 | Before defining interfaces       | protocol-vs-abc.md     |

## Where Triggers Live

| Location                   | Scope                     | Example                  |
| -------------------------- | ------------------------- | ------------------------ |
| AGENTS.md CRITICAL section | Repo-wide patterns        | `/tmp` → scratch storage |
| Skill files                | Domain-specific patterns  | EAFP → LBYL warning      |
| Slash command instructions | Command-specific patterns | Plan format requirements |

## Trigger vs Index

| Mechanism                   | When It Works                        | When It Fails                |
| --------------------------- | ------------------------------------ | ---------------------------- |
| **Index** (`read_when`)     | Agent actively searches for guidance | Agent doesn't know to search |
| **Trigger** (CRITICAL rule) | Agent is about to perform action     | Pattern not detected         |

**Use triggers for:** Common mistakes where agents don't know to look for docs
**Use index for:** Reference lookups where agents know they need guidance

## Adding New Triggers

When you discover a documentation gap where:

1. The doc exists
2. The doc is indexed
3. The agent still made the mistake

Add a behavioral trigger:

1. Identify the **action pattern** that preceded the mistake
2. Find the **documentation** that would have prevented it
3. Add a CRITICAL rule in AGENTS.md linking action → documentation

## Anti-Patterns

**❌ Too vague:**

```markdown
**CRITICAL: Be careful with files** → Read docs
```

**✅ Specific action pattern:**

```markdown
**CRITICAL: Before writing to `/tmp/`** → Read scratch-storage.md first.
```

**❌ Documentation that doesn't exist:**

```markdown
**CRITICAL: Before X** → Read nonexistent.md
```

**✅ Link to existing, indexed documentation:**

```markdown
**CRITICAL: Before X** → Read docs/agent/planning/scratch-storage.md first.
```
