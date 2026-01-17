# Documentation Plan: preprocess-session Output Options

## Context

The `erk exec preprocess-session` command gained two new options (`--output-dir` and `--prefix`) that work together to provide controlled output file naming with session IDs and automatic chunking.

**Key files:**
- `src/erk/cli/commands/exec/scripts/preprocess_session.py` - Implementation
- `.claude/commands/erk/learn.md` - Primary consumer of this feature

**The problem solved:**
Claude Code has a 25000 token limit for reading files. Large implementation sessions can exceed this limit, making them unreadable in a single file. The new options enable:
1. Automatic chunking via `--max-tokens`
2. Predictable file naming with session IDs
3. Output to a specified directory instead of temp files

## Raw Materials

https://gist.github.com/schrockn/3b7db83395faff052a0b9138f8af4b4e

## Documentation Items

### Item 1: Update `docs/learned/sessions/` with preprocessing guide

**Location:** `docs/learned/sessions/preprocessing.md` (new file)

**Action:** Create

**Content:**

```markdown
---
title: Session Preprocessing
read-when: Preprocessing Claude Code session logs for analysis
---

# Session Preprocessing

The `erk exec preprocess-session` command compresses JSONL session logs to XML format for efficient reading by Claude agents.

## Output Modes

### Temp Files (Default)

```bash
erk exec preprocess-session /path/to/session.jsonl
# Outputs: /tmp/session-{session-id}-compressed.xml
```

### Named Files with Session IDs

For workflows that need predictable file locations and names:

```bash
erk exec preprocess-session /path/to/session.jsonl \
    --output-dir ./output \
    --prefix planning
# Outputs: ./output/planning-{session-id}.xml
```

### Automatic Chunking

When sessions exceed Claude's read limit, use `--max-tokens` to split:

```bash
erk exec preprocess-session /path/to/session.jsonl \
    --max-tokens 20000 \
    --output-dir ./output \
    --prefix impl
# Outputs: ./output/impl-{session-id}-part1.xml
#          ./output/impl-{session-id}-part2.xml
#          ...
```

**Best practice:** Use `--max-tokens 20000` to stay safely under Claude's 25000 token read limit.

## Option Requirements

- `--output-dir` and `--prefix` must be used together
- `--output-dir`/`--prefix` cannot be combined with `--stdout`
- `--max-tokens` works with all output modes

## File Naming Patterns

| Mode | Single File | Multiple Chunks |
|------|-------------|-----------------|
| Temp files | `session-{id}-compressed.xml` | `session-{id}-part{N}-*.xml` |
| Named files | `{prefix}-{id}.xml` | `{prefix}-{id}-part{N}.xml` |

## Example: Learn Workflow

The `/erk:learn` command uses these options to preprocess sessions:

```bash
erk exec preprocess-session "<session-path>" \
    --max-tokens 20000 \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --prefix planning
```

This ensures:
1. Files are chunked if needed (readable by Claude)
2. Session IDs are in filenames (traceable)
3. Output goes to scratch storage (organized)
```

**Source:** [Impl] Implementation session and learn.md updates

### Item 2: Update index.md with new doc

**Location:** `docs/learned/index.md`

**Action:** Update - add entry for new preprocessing doc

**Content:** Add row to sessions section:
```
| [preprocessing.md](sessions/preprocessing.md) | Preprocessing session logs | Compressing sessions for analysis |
```