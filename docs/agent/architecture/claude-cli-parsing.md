---
title: Claude CLI Output Parsing
read_when:
  - "parsing Claude CLI output"
  - "extracting JSON from Claude --print mode"
  - "integrating with Claude CLI programmatically"
---

# Claude CLI Output Parsing

## The Problem

Claude CLI with `--print` mode outputs conversation/thinking text before the final JSON result:

```
Analyzing the session logs...
Found 3 relevant conversations.
Creating extraction plan...
{"issue_url": "https://github.com/user/repo/issues/123"}
```

Naive `json.loads(stdout)` fails because stdout isn't pure JSON.

## Solution: Search from End

Search backwards through output lines to find the JSON result:

```python
def extract_json_field(output: str, field: str) -> str | None:
    """Extract a field from JSON in mixed Claude CLI output."""
    if not output:
        return None

    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                value = data.get(field)
                if isinstance(value, str):
                    return value
        except json.JSONDecodeError:
            continue
    return None
```

## Why Search from End?

- Claude outputs thinking/progress text first, JSON result last
- The JSON is typically on the final non-empty line
- Searching backwards finds it immediately without parsing all the preamble

## Reference Implementation

See `_extract_issue_url_from_output()` in `src/erk/core/shell.py`
