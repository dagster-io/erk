---
title: Command Optimization Patterns
read_when:
  - "reducing command file size"
  - "using @ reference in commands"
  - "modularizing command content"
---

# Command Optimization Patterns

Patterns for reducing command file size and context consumption through modularization.

## Why Command Size Matters

Command text is loaded **every time** the command is invoked. Unlike skills (loaded once per session), commands consume context on each use.

| Content Type        | When Loaded      | Optimization Impact                 |
| ------------------- | ---------------- | ----------------------------------- |
| Command text        | Every invocation | High - reduce aggressively          |
| `@` referenced docs | Once per session | Medium - extract reference material |
| Skills              | Once per session | Low - already optimized             |

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
| Kit docs          | `@docs/erk/execution-guide.md`          | Relative to kit root   |
| Relative path     | `@../shared/common.md`                  | From command location  |

### Real Example: /fast-ci

**Command** (`.claude/commands/fast-ci.md`):

```markdown
---
description: Run fast CI checks iteratively
---

# /fast-ci

Run fast CI checks iteratively (unit tests + pyright).

@.claude/skills/ci-iteration/SKILL.md

## Implementation

Delegate to devrun agent with: "Run pytest tests/ && pyright"
```

**Referenced skill** (`ci-iteration` skill):

- Contains detailed iteration workflow (~246 lines)
- Loaded once per session
- Shared with `/all-ci` command

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

## Extraction Workflow

### Step 1: Identify Extractable Content

Look for:

- Sections >500 chars that are reference material
- Tables (standards, mappings, error codes)
- Step-by-step instructions that rarely change
- Content duplicated across commands

### Step 2: Create External Doc

```markdown
# [Descriptive Title]

[Content extracted from command]

## Section 1

...

## Section 2

...
```

**Placement:**

- Kit commands: `docs/<kit-name>/<command-name>/`

### Step 3: Replace with Reference

Before:

```markdown
### Step 4: Execute phases

#### Context Consumption

[800 chars of guidance]

#### Phase Execution Process

[1500 chars of detailed steps]

#### Coding Standards

[700 chars of table]
```

After:

```markdown
### Step 4: Execute phases

**MANDATORY**: Load `fake-driven-testing` skill for test guidance.

@docs/erk/plan-implement/execution-guide.md

For each phase:

1. Mark phase as `in_progress`
2. Implement code AND tests
3. Mark complete
```

### Step 4: Build Artifacts

After creating the external doc, run:

```bash
erk dev kit-build
```

This syncs the documentation to kit packages.

## Size Targets

| Artifact Type  | Target Size  | Maximum      |
| -------------- | ------------ | ------------ |
| Commands       | <5,000 chars | 8,000 chars  |
| Skills (core)  | <3,000 chars | 5,000 chars  |
| Skills (total) | <8,000 chars | 12,000 chars |
| External docs  | No limit     | Keep focused |

## Measuring Success

Before optimization:

```bash
wc -c .claude/commands/my-command.md
# 13,397 chars
```

After optimization:

```bash
wc -c .claude/commands/my-command.md
# 7,000 chars (-48%)
```

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

### Forgetting to Build

```bash
# DON'T: Create doc without building

# DO: Run kit-build after creating docs
erk dev kit-build
```

## Case Study: /erk:plan-implement

**Before**: 13,397 chars loaded every invocation

- Step 4: 2,000+ chars of execution details
- Step 5: Duplicate of Step 4 content
- Steps 7-8: Could be merged

**After**: ~7,000 chars + 3,700 char external doc

- Extracted execution guide to `@docs/erk/plan-implement/execution-guide.md`
- Deleted redundant Step 5
- Merged Steps 7-8

**Result**: 48% reduction in per-invocation context consumption

## Related Documentation

- [Context Analysis](../sessions/context-analysis.md) - Analyzing context consumption
- [Agent Delegation](../planning/agent-delegation.md) - Delegating to agents (another optimization)
