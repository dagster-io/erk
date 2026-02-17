---
title: Command Optimization Patterns
read_when:
  - "reducing command file size"
  - "using @ reference in commands"
  - "modularizing command content"
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# Command Optimization Patterns

Patterns for reducing command file size and context consumption through modularization.

## Why Command Size Matters

Since Claude Code 2.1.0, commands and skills are equivalent - both are loaded when invoked. Command text in `.claude/commands/` behaves identically to skills in `.claude/skills/`.

| Content Type        | When Loaded                           | Optimization Impact                 |
| ------------------- | ------------------------------------- | ----------------------------------- |
| Command/skill text  | When invoked (unless cached)          | High - reduce aggressively          |
| `@` referenced docs | Once per session (cached after first) | Medium - extract reference material |

## The @ Reference Pattern

### Syntax

Place an `@` reference on its own line to include external documentation:

```markdown
### Step 4: Execute phases

@docs/execution-guide.md

For each phase, follow the guide above.
```

### How It Works

1. Claude Code expands `@path/to/doc.md` to the file contents
2. Expansion happens once per session (cached)
3. Multiple references to same doc don't duplicate content

### Valid Locations

| Location          | Example                                 | Notes                  |
| ----------------- | --------------------------------------- | ---------------------- |
| `.claude/skills/` | `@.claude/skills/ci-iteration/SKILL.md` | Project-specific skill |
| Relative path     | `@../shared/common.md`                  | From command location  |

## When to Extract

### Good Candidates for Extraction

| Content Type               | Example                         | Why Extract                        |
| -------------------------- | ------------------------------- | ---------------------------------- |
| Reference tables           | Coding standards, error codes   | Loaded once, referenced many times |
| Detailed step instructions | Multi-step workflows            | Changes rarely, bulky inline       |
| Shared content             | Common patterns across commands | Single source of truth             |
| Examples                   | Sample code, templates          | Reference material                 |

### Keep Inline

| Content Type            | Example                       | Why Keep                         |
| ----------------------- | ----------------------------- | -------------------------------- |
| Critical decision logic | "If X then do Y"              | Must be visible every invocation |
| Short unique content    | Command-specific instructions | Overhead of separate file        |
| Frequently changing     | Active development            | Easier to maintain inline        |

## Size Targets

| Artifact Type  | Target Size  | Maximum      |
| -------------- | ------------ | ------------ |
| Commands       | <5,000 chars | 8,000 chars  |
| Skills (core)  | <3,000 chars | 5,000 chars  |
| Skills (total) | <8,000 chars | 12,000 chars |
| External docs  | No limit     | Keep focused |

## Anti-Patterns

### Extracting Critical Logic

```markdown
# DON'T: Extract decision points

@docs/when-to-stop.md # User won't see this every time!

# DO: Keep inline

**When to Stop:**

- All checks pass → SUCCESS
- Same error 3x → STUCK
- 10 iterations → STUCK
```

### Too Many Small Docs

```markdown
# DON'T: Fragment excessively

@docs/step1.md
@docs/step2.md
@docs/step3.md
@docs/step4.md

# DO: Group related content

@docs/execution-workflow.md
```

## Related Documentation

- [Context Analysis](../sessions/context-analysis.md) - Analyzing context consumption
- [Agent Delegation](../planning/agent-delegation.md) - Delegating to agents (another optimization)
