---
title: LLM JSON Parsing
read_when:
  - "parsing JSON from LLM text output"
  - "extracting structured data from Claude responses"
  - "writing code that processes LLM-generated JSON"
tripwires:
  - action: "writing manual fence-stripping code to extract JSON from LLM output"
    warning: "Use extract_json_dict() from erk.core.llm_json instead. It handles fences, preamble, and trailing text via raw_decode()."
    score: 6
  - action: "using regex to extract JSON from LLM output"
    warning: "Use extract_json_dict() which uses JSONDecoder.raw_decode() — more robust than regex for nested JSON structures."
    score: 5
---

# LLM JSON Parsing

LLMs sometimes wrap their JSON in markdown fences or add trailing commentary. The `extract_json_dict()` function provides robust extraction using `json.JSONDecoder.raw_decode()`.

## The Function

<!-- Source: src/erk/core/llm_json.py, extract_json_dict -->

`extract_json_dict()` in `src/erk/core/llm_json.py` extracts the first JSON dict from arbitrary LLM text output.

**Algorithm:**

1. Find first `{` character in the text
2. Use `JSONDecoder.raw_decode()` starting at that position
3. Verify the parsed result is a dict (not a list or primitive)
4. Return `None` for any failure (empty text, no `{`, parse error, non-dict result)

## Usage

<!-- Source: src/erk/core/plan_duplicate_checker.py, extract_json_dict -->

Used in two callers:

- `plan_duplicate_checker.py` — parses LLM duplicate detection responses
- `plan_relevance_checker.py` — parses LLM relevance assessment responses

## Why raw_decode()

`json.loads()` requires the entire input to be valid JSON. `raw_decode()` parses the first valid JSON value from a starting position, ignoring everything after. This handles:

- Markdown fence wrappers (` ```json ... ``` `)
- Preamble text ("Here's the result: {...")
- Trailing commentary ("...} Let me know if you need more")
- Multiple JSON objects (extracts only the first)

## Anti-Patterns

**Never write manual fence-stripping code:**

````python
# WRONG: fragile, misses edge cases
text = text.strip("```json").strip("```")
result = json.loads(text)
````

**Never use regex for JSON extraction:**

```python
# WRONG: breaks on nested braces
match = re.search(r'\{.*\}', text, re.DOTALL)
```

## Related Documentation

- [Source Pointers](../documentation/source-pointers.md) — Format for code references in docs
