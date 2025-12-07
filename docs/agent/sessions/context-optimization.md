---
title: Context Window Optimization
read_when:
  - "analyzing session efficiency"
  - "troubleshooting context limits"
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

- Look for `cache_creation_input_tokens` jumps
- Context resets (drops >50%) indicate compaction occurred
