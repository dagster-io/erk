---
title: Session Preprocessing
read_when:
  - "preprocessing Claude Code session logs for analysis"
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

| Mode        | Single File                   | Multiple Chunks              |
| ----------- | ----------------------------- | ---------------------------- |
| Temp files  | `session-{id}-compressed.xml` | `session-{id}-part{N}-*.xml` |
| Named files | `{prefix}-{id}.xml`           | `{prefix}-{id}-part{N}.xml`  |

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

## Related Documentation

- [tools.md](tools.md) - Session analysis tools overview
- [layout.md](layout.md) - Session log format specification
