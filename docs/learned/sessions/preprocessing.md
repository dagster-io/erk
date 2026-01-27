---
title: Session Preprocessing
read_when:
  - "preprocessing Claude Code session logs for analysis"
---

# Session Preprocessing

The `erk exec preprocess-session` command compresses JSONL session logs to XML format for efficient reading by Claude agents.

## Compression Metrics

Real-world compression performance from erk sessions:

| Session Type           | JSONL Size | XML Size | Reduction | Ratio |
| ---------------------- | ---------- | -------- | --------- | ----- |
| Planning session       | 157 KB     | 25 KB    | 132 KB    | 84%   |
| Implementation session | 420 KB     | 68 KB    | 352 KB    | 84%   |
| Large implementation   | 1.2 MB     | 195 KB   | 1.0 MB    | 84%   |

**Key insight:** Preprocessing achieves consistent ~84% size reduction regardless of session size.

### What Gets Compressed

- **Removed**: System messages, internal metadata, token usage stats
- **Preserved**: User messages, assistant responses, tool calls, tool results
- **Format**: Compact XML tags instead of verbose JSON

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

### Chunking Algorithm

When a session exceeds `--max-tokens`:

1. **Split at message boundaries** - Never break mid-message
2. **Name parts sequentially** - `part1.xml`, `part2.xml`, etc.
3. **Preserve context** - Each part is self-contained XML
4. **Track part count** - Agents know total parts upfront

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

## Token Compression Ratios

Session preprocessing achieves **71-92% token compression**:

| Raw Tokens | Preprocessed Tokens | Compression Ratio |
| ---------- | ------------------- | ----------------- |
| 100K       | 25K                 | 75%               |
| 50K        | 14K                 | 72%               |
| 200K       | 58K                 | 71%               |
| 30K        | 9K                  | 70%               |

**Average:** ~75% compression

### What Gets Compressed by Type

| Content Type         | Compression |
| -------------------- | ----------- |
| Repeated system msgs | 95%+        |
| Tool outputs         | 60-80%      |
| User messages        | 10-20%      |
| Assistant responses  | 20-40%      |

### Implications

A 100K raw session:

- **After preprocessing:** ~25K tokens
- **If > 20K:** Split into 2 parts (part1: 20K, part2: 5K)
- **Total files:** 2 files

Even very large sessions (200K raw) typically fit in 3-4 parts after preprocessing.

## Multi-Part File Handling

### Part Numbering

Multi-part files use 1-indexed numbering:

```
<session_id>.part1.jsonl
<session_id>.part2.jsonl
<session_id>.part3.jsonl
```

### Downstream Processing Patterns

#### Pattern 1: Check for Parts

```bash
SESSION_ID="abc123-def456-789"
BASE_FILE=~/.claude/projects/erk/sessions/${SESSION_ID}.jsonl

if [ -f "${BASE_FILE}" ]; then
  # Single-file session
  SESSION_FILES="${BASE_FILE}"
elif [ -f "${BASE_FILE%.jsonl}.part1.jsonl" ]; then
  # Multi-part session
  SESSION_FILES="${BASE_FILE%.jsonl}.part*.jsonl"
else
  echo "Session ${SESSION_ID} not found"
fi
```

#### Pattern 2: Sequential Processing

Process parts in order:

```bash
for part in ${SESSION_ID}.part*.jsonl; do
  echo "Processing $part"
  # Analyze part
done
```

#### Pattern 3: Combined Analysis

Combine parts for full session analysis:

```bash
# Concatenate all parts
cat ${SESSION_ID}.part*.jsonl > ${SESSION_ID}.combined.jsonl

# Analyze combined session
analyze-session ${SESSION_ID}.combined.jsonl
```

## Related Documentation

- [Session Lifecycle](lifecycle.md) - Session file persistence and availability
- [Session Discovery](discovery-fallback.md) - Enumerating and finding sessions
- [tools.md](tools.md) - Session analysis tools overview
- [layout.md](layout.md) - Session log format specification
