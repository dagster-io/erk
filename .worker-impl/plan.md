# Plan: Extend tools.md with Documentation Observability

## Goal

Extend `docs/learned/sessions/tools.md` with documentation observability recipes and analysis patterns.

## Context

Existing documentation already covers:
- `layout.md` - Directory structure, file types, session IDs (765 lines)
- `jsonl-schema-reference.md` - Entry types, content blocks, tool schemas (761 lines)
- `tools.md` - CLI commands and analysis recipes (305 lines)

**User decision:** Extend `tools.md` rather than create a new doc.

## Key Findings to Document

### 1. What's Extractable for Doc Observability

| Data Point | Source | Extraction |
|------------|--------|------------|
| Doc file reads | `Read` tool_use with `docs/learned/**` path | Easy |
| Skill loads | `Skill` tool_use with skill name | Easy |
| Thinking/reasoning | `content[].type == "thinking"` | Easy |
| WebFetch content | tool_result for WebFetch (AI summary) | Easy |
| WebSearch results | tool_result for WebSearch (links + titles) | Easy |
| Tool errors | tool_result with `is_error=true` | Easy |
| User prompts | `type=user, userType=external` | Easy |

### 2. Practical jq Queries for Doc Analytics

```bash
# Count docs/learned reads across all sessions
cat *.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "tool_use" and .name == "Read") |
  .input.file_path
' | grep "docs/learned" | sort | uniq -c | sort -rn

# Count skill loads
cat *.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "tool_use" and .name == "Skill") |
  .input.skill
' | sort | uniq -c | sort -rn

# Extract thinking blocks
cat session.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "thinking") |
  {length: (.thinking | length), preview: (.thinking | .[0:200])}
'
```

### 3. Documentation Observability Goals

1. **Assess value** - Which docs are used? Which are never accessed?
2. **Debug routing** - Are tripwires firing? Are skills loading when they should?
3. **Identify gaps** - What docs should exist but don't?

### 4. Sample Data from erk Project

From 988 sessions:
- Top docs: `hooks/hooks.md` (13), `tripwires.md` (12), `index.md` (12)
- Top skills: `fake-driven-testing` (49), `dignified-python-*` (89 combined)
- 1563 tool errors across all sessions

### 5. Thinking Block Analysis

Thinking is fully persisted as `content[].type == "thinking"` with:
- Full reasoning text
- Can analyze for implicit doc references
- Can detect uncertainty signals
- Can understand decision rationale

### 6. Web Tool Results

**WebFetch** - Returns AI-summarized content from URLs
**WebSearch** - Returns query + link titles + URLs

Both fully persisted in tool_result content.

## File to Modify

**Path:** `docs/learned/sessions/tools.md`

**Add new section after "## Debugging Workflows":**

```markdown
## Documentation Observability

Recipes for measuring learned docs effectiveness using session logs.

### Extractable Signals

| Data Point | Source | Extraction |
|------------|--------|------------|
| Doc file reads | `Read` tool_use with `docs/learned/**` path | Easy |
| Skill loads | `Skill` tool_use with skill name | Easy |
| Thinking/reasoning | `content[].type == "thinking"` | Easy |
| WebFetch content | tool_result for WebFetch (AI summary) | Easy |
| WebSearch results | tool_result for WebSearch (links + titles) | Easy |
| Tool errors | tool_result with `is_error=true` | Easy |
| User prompts | `type=user, userType=external` | Easy |

### Count docs/learned Reads

\`\`\`bash
cat *.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "tool_use" and .name == "Read") |
  .input.file_path
' | grep "docs/learned" | sort | uniq -c | sort -rn
\`\`\`

### Count Skill Loads

\`\`\`bash
cat *.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "tool_use" and .name == "Skill") |
  .input.skill
' | sort | uniq -c | sort -rn
\`\`\`

### Extract Thinking Blocks

Thinking is fully persisted and can be analyzed for:
- Implicit doc references (mentioned but not Read)
- Uncertainty signals ("might", "not sure")
- Decision rationale

\`\`\`bash
cat session.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "thinking") |
  {length: (.thinking | length), preview: (.thinking | .[0:200])}
'
\`\`\`

### WebFetch/WebSearch Results

Web tool results are fully persisted:
- **WebFetch**: AI-summarized content from URLs
- **WebSearch**: Query + link titles + URLs

\`\`\`bash
# Find WebFetch tool uses and results
cat session.jsonl | jq -c '
  select(.type == "assistant") |
  .message.content[]? |
  select(.type == "tool_use" and .name == "WebFetch") |
  {id: .id, url: .input.url, prompt: .input.prompt}
'
\`\`\`

### Correlate Doc Reads with Errors

\`\`\`bash
# Count tool errors per session
cat session.jsonl | jq -c '
  select(.type == "user") |
  .message.content[]? |
  select(.type == "tool_result" and .is_error == true)
' | wc -l
\`\`\`

### Sample Analytics from erk Project

From 988 sessions:
- Top docs: `hooks/hooks.md` (13), `tripwires.md` (12), `index.md` (12)
- Top skills: `fake-driven-testing` (49), `dignified-python-*` (89 combined)
- 1563 tool errors across all sessions

### Limitations

**What can't be measured:**
- Mental reference (Claude "remembers" doc content without re-reading)
- Session outcome quality (success/failure)
- Why a doc wasn't loaded (negative signal)
- Context window consumption per doc
```

**Also update frontmatter `read_when` to include:**
```yaml
read_when:
  - "finding session logs"
  - "inspecting agent execution"
  - "debugging session issues"
  - "measuring learned docs effectiveness"
  - "analyzing which docs are used"
```

## Implementation Steps

1. Edit `docs/learned/sessions/tools.md`:
   - Add doc observability `read_when` entries to frontmatter
   - Add new "## Documentation Observability" section after "## Debugging Workflows"
2. Run `erk docs sync` to update index.md

## Related Documentation

Skills to load: `learned-docs` (for doc formatting conventions)