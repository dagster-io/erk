---
description: Analyze context window usage for all sessions in the current worktree
---

# /erk:analyze-context

Analyzes context window usage across all sessions in the current worktree, showing token breakdown by category.

## Usage

```bash
/erk:analyze-context
```

## Output

Displays:

- Summary metrics (sessions analyzed, peak context, cache hit rate)
- Token breakdown by category (file reads, assistant responses, tool results, etc.)
- Duplicate file reads across sessions

---

## Agent Instructions

### Step 1: Discover Sessions

Run the command to get all sessions for this worktree:

```bash
erk exec list-sessions --min-size 1000
```

Parse the JSON output which contains:

- `success`: Whether the operation succeeded
- `sessions`: List of session objects with `session_id` and file metadata
- `project_dir`: Path to the project directory containing session JSONL files

If `success` is false or no sessions found, display:

```
No sessions found for this worktree (or sessions too small to analyze).
```

### Step 2: Parse Each Session JSONL

For each session in the list, read the JSONL file at:

```
{project_dir}/session_{session_id}.jsonl
```

Parse each line as JSON. The JSONL contains messages with different structures:

**API Response messages** (contain token usage):

```json
{
  "type": "assistant",
  "message": {
    "usage": {
      "input_tokens": 12345,
      "output_tokens": 678,
      "cache_read_input_tokens": 10000,
      "cache_creation_input_tokens": 2000
    }
  }
}
```

**Tool use messages** (track tool invocations):

```json
{
  "type": "assistant",
  "message": {
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_xxx",
        "name": "Read",
        "input": { "file_path": "/path/to/file.py" }
      }
    ]
  }
}
```

**Tool result messages** (contain the actual content):

```json
{
  "type": "user",
  "message": {
    "content": [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_xxx",
        "content": "... file contents ..."
      }
    ]
  }
}
```

**User text messages**:

```json
{
  "type": "user",
  "message": {
    "content": "user's message text"
  }
}
```

### Step 3: Build Tool Correlation Map

For each session, build a map from `tool_use_id` to tool metadata:

```python
tool_map = {}  # tool_use_id -> {"name": "Read", "input": {...}}

# When you see a tool_use block:
tool_map[block["id"]] = {
    "name": block["name"],
    "input": block.get("input", {})
}
```

This allows categorizing tool results by their originating tool.

### Step 4: Categorize Content

For each piece of content, categorize and estimate tokens:

| Category               | Detection Method                                                       |
| ---------------------- | ---------------------------------------------------------------------- |
| **File reads**         | Tool result where `tool_map[id].name == "Read"`                        |
| **Skill expansions**   | Content contains "skill is running" or "Base directory for this skill" |
| **Command prompts**    | Content starts with `# /` or contains `<command-message>`              |
| **CLAUDE.md context**  | Content contains "CLAUDE.md" or "AGENTS.md"                            |
| **Bash/tool results**  | Tool result where name is "Bash", "Grep", "Glob", etc.                 |
| **Assistant output**   | Use `output_tokens` from usage data                                    |
| **Other user content** | Remaining user message text                                            |

**Token estimation formula** (when actual counts unavailable):

```python
estimated_tokens = len(text) // 4
```

**Track per category**:

```python
categories = {
    "file_reads": 0,
    "skill_expansions": 0,
    "command_prompts": 0,
    "claude_md_context": 0,
    "bash_tool_results": 0,
    "assistant_output": 0,
    "other_user_content": 0,
}
```

### Step 5: Track File Read Duplicates

Maintain a dictionary of file paths read across all sessions:

```python
file_read_counts = {}  # file_path -> count
file_read_tokens = {}  # file_path -> estimated tokens

# When categorizing a Read tool result:
file_path = tool_map[tool_use_id]["input"].get("file_path", "unknown")
tokens = len(content) // 4
file_read_counts[file_path] = file_read_counts.get(file_path, 0) + 1
file_read_tokens[file_path] = tokens  # Last value is fine for estimation
```

### Step 6: Calculate Aggregate Metrics

**Per-session metrics**:

```python
session_metrics = {
    "total_input_tokens": sum of input_tokens from usage,
    "total_output_tokens": sum of output_tokens from usage,
    "cache_read_tokens": sum of cache_read_input_tokens,
    "cache_creation_tokens": sum of cache_creation_input_tokens,
}
```

**Peak context** (highest single message context):

```python
peak_context = max(cache_read + cache_creation for each usage block)
```

**Cache hit rate**:

```python
total_cache_read = sum of all cache_read_input_tokens
total_cache_creation = sum of all cache_creation_input_tokens
cache_hit_rate = total_cache_read / (total_cache_read + total_cache_creation) * 100
```

### Step 7: Generate Output

Format results as markdown:

```markdown
## Context Analysis Summary

| Metric              | Value                 |
| ------------------- | --------------------- |
| Sessions analyzed   | X                     |
| Peak context window | X tokens (Y% of 200K) |
| Cache hit rate      | X%                    |

## Token Breakdown by Category

| Category            | Tokens | % of Total |
| ------------------- | ------ | ---------- |
| File reads          | X      | Y%         |
| Assistant responses | X      | Y%         |
| Other user content  | X      | Y%         |
| Command prompts     | X      | Y%         |
| Skill expansions    | X      | Y%         |
| CLAUDE.md context   | X      | Y%         |
| Bash/tool results   | X      | Y%         |

## Duplicate Reads

X files were read multiple times across sessions (~Y tokens could be saved)

| File            | Times Read | Est. Tokens |
| --------------- | ---------- | ----------- |
| path/to/file.py | 3          | 1,234       |
```

**Notes for output**:

- Sort categories by token count descending
- Only show duplicate reads where count > 1
- Sort duplicate reads by (count \* tokens) descending (highest waste first)
- Truncate file paths if too long (show last 50 chars with `...` prefix)
- Format large numbers with commas (e.g., 12,345)
- Calculate percentage relative to 200,000 token context window

### Error Handling

- **Malformed JSONL lines**: Skip the line and continue processing
- **Missing usage data**: Estimate from content length using `len(text) // 4`
- **Missing tool_use_id in tool_map**: Categorize as "other_user_content"
- **Empty sessions**: Should be filtered by `--min-size` but skip if encountered

### Example Implementation (Python-like pseudocode)

```python
import json

# Step 1: Get sessions
sessions_json = run("erk exec list-sessions --min-size 1000")
data = json.loads(sessions_json)

if not data["success"] or not data["sessions"]:
    print("No sessions found")
    return

project_dir = data["project_dir"]
sessions = data["sessions"]

# Initialize aggregates
categories = {k: 0 for k in ["file_reads", "skill_expansions", "command_prompts",
                             "claude_md_context", "bash_tool_results",
                             "assistant_output", "other_user_content"]}
file_read_counts = {}
file_read_tokens = {}
peak_context = 0
total_cache_read = 0
total_cache_creation = 0

for session in sessions:
    jsonl_path = f"{project_dir}/session_{session['session_id']}.jsonl"
    tool_map = {}

    for line in read_lines(jsonl_path):
        try:
            entry = json.loads(line)
        except:
            continue

        msg = entry.get("message", {})
        content = msg.get("content", "")

        # Extract usage
        usage = msg.get("usage", {})
        if usage:
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            total_cache_read += cache_read
            total_cache_creation += cache_create
            peak_context = max(peak_context, cache_read + cache_create)
            categories["assistant_output"] += usage.get("output_tokens", 0)

        # Build tool map
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    tool_map[block["id"]] = {
                        "name": block["name"],
                        "input": block.get("input", {})
                    }
                elif block.get("type") == "tool_result":
                    tool_id = block.get("tool_use_id")
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        tokens = len(result_content) // 4
                        tool_info = tool_map.get(tool_id, {})
                        tool_name = tool_info.get("name", "")

                        if tool_name == "Read":
                            categories["file_reads"] += tokens
                            fp = tool_info.get("input", {}).get("file_path", "unknown")
                            file_read_counts[fp] = file_read_counts.get(fp, 0) + 1
                            file_read_tokens[fp] = tokens
                        elif tool_name in ["Bash", "Grep", "Glob"]:
                            categories["bash_tool_results"] += tokens
                        elif "skill is running" in result_content or "Base directory" in result_content:
                            categories["skill_expansions"] += tokens
                        elif result_content.startswith("# /") or "<command-message>" in result_content:
                            categories["command_prompts"] += tokens
                        elif "CLAUDE.md" in result_content or "AGENTS.md" in result_content:
                            categories["claude_md_context"] += tokens
                        else:
                            categories["other_user_content"] += tokens
        elif isinstance(content, str):
            tokens = len(content) // 4
            if "skill is running" in content or "Base directory" in content:
                categories["skill_expansions"] += tokens
            elif content.startswith("# /") or "<command-message>" in content:
                categories["command_prompts"] += tokens
            elif "CLAUDE.md" in content or "AGENTS.md" in content:
                categories["claude_md_context"] += tokens
            else:
                categories["other_user_content"] += tokens

# Calculate metrics
total_tokens = sum(categories.values())
cache_total = total_cache_read + total_cache_creation
cache_hit_rate = (total_cache_read / cache_total * 100) if cache_total > 0 else 0
peak_pct = (peak_context / 200000 * 100)

# Find duplicates
duplicates = {k: v for k, v in file_read_counts.items() if v > 1}
wasted_tokens = sum((v - 1) * file_read_tokens.get(k, 0) for k, v in duplicates.items())
```
