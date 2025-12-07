---
title: Context Window Optimization
read_when:
  - "analyzing session efficiency"
  - "troubleshooting context limits"
  - "reducing context waste"
tripwire: false
---

# Context Window Optimization

Patterns discovered through session analysis for reducing context waste.

## Common Context Waste Patterns

### 1. Duplicate File Reads

**Problem:** Reading the same file multiple times within a session wastes context.

**Detection:** Use session preprocessing to identify files read more than once:

```bash
dot-agent run erk preprocess-session <session.jsonl> --stdout | grep -o 'file_path">[^<]*' | sort | uniq -c | sort -rn
```

**Prevention:**

- Read files once, reference line numbers in subsequent operations
- Use Edit tool's context awareness instead of re-reading

### 2. Skill Loading Overhead

Skills like `dignified-python-313` and `fake-driven-testing` add ~15-20K tokens per load.

**Optimization:**

- Skills persist for entire session - never reload
- Hook reminders are safety nets, not commands to reload
- Check for `<command-message>The "{name}" skill is loading</command-message>` before loading

### 3. Agent Subprocess Inefficiency

Small agent outputs (<5KB) may indicate tasks that didn't need delegation.

**When to use agents:**

- Exploration across multiple files
- Tasks requiring specialized parsing (devrun)
- Parallel independent searches

**When NOT to use agents:**

- Single file reads
- Simple grep operations
- Tasks with obvious single answers

## Context Budget Guidelines

| Session Type     | Target Peak  | Warning |
| ---------------- | ------------ | ------- |
| Quick task       | <50K tokens  | >75K    |
| Feature impl     | <100K tokens | >150K   |
| Complex refactor | <150K tokens | >180K   |

## Monitoring Context Growth

Track context growth by examining token usage in session logs:

### Key Indicators

- **`cache_creation_input_tokens`**: Large jumps indicate new content loaded
- **Context drops (>50%)**: Indicates compaction/summarization occurred
- **Repeated tool result sizes**: May indicate duplicate operations

### Analysis Commands

```bash
# View token usage over time
cat session.jsonl | jq -s '[.[] | select(.usage) | {
  turn: .turn_number,
  input: .usage.input_tokens,
  output: .usage.output_tokens,
  cache_read: .usage.cache_read_input_tokens
}]'
```

## Optimization Strategies

### For Exploration Tasks

1. **Use Explore agent for broad searches** - Aggregates results efficiently
2. **Narrow glob patterns** - `src/**/*.py` not `**/*.py`
3. **Limit grep output** - Use `head_limit` parameter

### For Implementation Tasks

1. **Read context once at start** - Load all relevant files early
2. **Reference line numbers** - Don't re-read for edits
3. **Batch related edits** - Multiple edits to same file in sequence

### For CI/Testing Tasks

1. **Use devrun agent** - Parses output efficiently
2. **Filter test output** - Only relevant failures
3. **Avoid verbose flags** - Unless debugging specific issues

## Related Documentation

- [Session Log Analysis Tools](tools.md) - CLI commands for analysis
- [Context Analysis](context-analysis.md) - Detailed context consumption analysis
