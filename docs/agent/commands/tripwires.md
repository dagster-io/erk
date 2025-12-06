---
title: Tripwires
read_when:
  - "adding documentation routing rules"
  - "making documentation more discoverable"
  - "preventing common agent mistakes"
---

# Tripwires

Tripwires are action-triggered rules ("if you're about to do X, consult Y") that route agents to documentation when specific action patterns are detected.

## The Problem

Documentation can exist and be indexed, but agents may still make mistakes because:

1. The agent doesn't know to look for the documentation
2. The action happens before the agent thinks to check docs
3. The "read when" conditions in docs aren't triggered by the specific action

## The Pattern

Tripwires are defined in frontmatter of agent documentation files:

```yaml
---
title: Scratch Storage
read_when:
  - "writing temp files for AI workflows"
tripwires:
  - action: "writing to /tmp/"
    warning: "AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/."
---
```

When `dot-agent docs sync` runs, it collects all tripwires and generates `docs/agent/generated/tripwires.md`, which is included via `@` reference in AGENTS.md. See [AGENT-DOC-STANDARD.md](../../AGENT-DOC-STANDARD.md) for the complete frontmatter specification.

### Generated Output

```markdown
**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](../planning/scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.
```

### Examples

| Action Pattern                      | Tripwire                         | Source Doc             |
| ----------------------------------- | -------------------------------- | ---------------------- |
| Writing to `/tmp/`                  | Before writing temp files        | scratch-storage.md     |
| Using `try/except` for control flow | Before adding exception handling | dignified-python skill |
| Creating a Protocol                 | Before defining interfaces       | protocol-vs-abc.md     |

## Where Tripwires Are Defined

| Location                       | Scope                     | Example                  |
| ------------------------------ | ------------------------- | ------------------------ |
| Doc frontmatter (`tripwires:`) | Per-doc patterns          | `/tmp` → scratch storage |
| Skill files                    | Domain-specific patterns  | EAFP → LBYL warning      |
| AGENTS.md (manual CRITICAL)    | Repo-wide static patterns | Never commit to master   |

## Tripwire vs Index

| Mechanism                       | When It Works                        | When It Fails                |
| ------------------------------- | ------------------------------------ | ---------------------------- |
| **Index** (`read_when`)         | Agent actively searches for guidance | Agent doesn't know to search |
| **Tripwire** (action + warning) | Agent is about to perform action     | Pattern not detected         |

**Use tripwires for:** Common mistakes where agents don't know to look for docs
**Use index for:** Reference lookups where agents know they need guidance

## Adding New Tripwires

When you discover a documentation gap where:

1. The doc exists
2. The doc is indexed
3. The agent still made the mistake

Add a tripwire to the relevant doc's frontmatter:

1. Identify the **action pattern** that preceded the mistake
2. Find the **documentation** that would have prevented it
3. Add a `tripwires:` entry with `action` and `warning` fields
4. Run `dot-agent docs sync` to regenerate the tripwires file

## Anti-Patterns

**❌ Too vague:**

```yaml
tripwires:
  - action: "working with files"
    warning: "Read docs"
```

**✅ Specific action pattern:**

```yaml
tripwires:
  - action: "writing to /tmp/"
    warning: "AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/."
```

**❌ Warning without context:**

```yaml
tripwires:
  - action: "using session data"
    warning: "Be careful"
```

**✅ Actionable warning:**

```yaml
tripwires:
  - action: "working with session-specific data"
    warning: 'Multiple sessions can run in parallel. NEVER use "most recent by mtime" - always scope by session ID.'
```
