# Documentation Plan: Extract JSON with raw_decode; convert erk-slack-bot to synchronous

## Context

This plan documents insights from PR #8055, which replaced brittle fence-stripping logic with a robust JSON extraction utility using `json.JSONDecoder.raw_decode()`. The old pattern (`fence_lines[1:-1]`) broke when LLMs added trailing commentary after closing markdown fences, which happened in production with `erk plan duplicate-check`.

The new `extract_json_dict()` utility in `erk.core.llm_json` provides a single, reusable solution for extracting JSON from LLM output. It handles markdown fences, preamble text, and trailing commentary robustly via `raw_decode()`. This pattern is immediately applicable to any command that calls `claude --print --output-format text` or any integration that parses JSON from unstructured LLM output.

Documentation matters here because the solution involves a non-obvious Python standard library method (`JSONDecoder.raw_decode()`) that future agents are unlikely to discover independently. Without documentation, agents will repeatedly write brittle fence-stripping code that eventually breaks in production.

**Note on scope:** The plan title mentions "convert erk-slack-bot to synchronous" but the actual PR diff only contains LLM JSON extraction changes. This documentation plan focuses exclusively on the LLM JSON parsing pattern.

## Raw Materials

PR #8055: https://github.com/schrockn/erk/pull/8055

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. extract_json_dict() usage tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8055]

**Draft Content:**

```markdown
**parsing JSON from LLM output (claude --print --output-format text)** → Read [LLM JSON Parsing Reference](../reference/llm-json-parsing.md) first. ALWAYS use `extract_json_dict()` from `erk.core.llm_json`. NEVER write fence-stripping logic (brittle, breaks on trailing text). Handles markdown fences, preamble, trailing commentary via `json.JSONDecoder.raw_decode()`.
```

---

#### 2. json.JSONDecoder.raw_decode() pattern tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8055]

**Draft Content:**

```markdown
**extracting JSON from unstructured text (LLM output, logs, mixed content)** → Read [LLM JSON Parsing Reference](../reference/llm-json-parsing.md) first. Use `json.JSONDecoder.raw_decode()` instead of json.loads(). Pattern finds first '{' and parses from that position, ignoring preamble and trailing text. Returns tuple: (parsed_object, end_position).
```

---

### MEDIUM Priority

#### 1. LLM JSON parsing reference documentation

**Location:** `docs/learned/reference/llm-json-parsing.md`
**Action:** CREATE
**Source:** [PR #8055]

**Draft Content:**

```markdown
---
title: LLM JSON Parsing Reference
read_when:
  - "parsing JSON from LLM output"
  - "extracting structured data from claude --print"
  - "handling JSON wrapped in markdown fences"
tripwires:
  - trigger: "parsing JSON from LLM output"
    warning: "ALWAYS use extract_json_dict() from erk.core.llm_json"
---

# LLM JSON Parsing Reference

When parsing JSON from LLM output, always use the `extract_json_dict()` utility from `erk.core.llm_json`.

## Why Not json.loads()?

LLMs (especially Haiku) often wrap JSON in markdown fences with additional text:
- Preamble: "Here's the JSON response:"
- Fences: Triple backticks with language hints
- Trailing commentary: "Let me know if you need anything else!"

Manual fence-stripping (`fence_lines[1:-1]`) assumes the last line is the closing fence. This breaks when trailing text follows.

## The Solution: raw_decode()

`json.JSONDecoder.raw_decode()` finds the first JSON object in arbitrary text:

1. Find the first `{` character
2. Parse JSON starting from that position
3. Return the parsed object and the end position
4. Ignore everything before and after

## Usage

```python
from erk.core.llm_json import extract_json_dict

llm_output = """Here's the analysis:
```json
{"is_duplicate": true, "confidence": 0.95}
```
Hope this helps!"""

result = extract_json_dict(llm_output)
# Returns: {"is_duplicate": True, "confidence": 0.95}
```

## Error Handling

`extract_json_dict()` returns `None` for:
- Empty input text
- No `{` found in text
- JSON parse errors (ValueError/TypeError from decoder)
- Parsed result is not a dict (e.g., JSON array)

This is an error boundary for the json module, not EAFP. The try/except catches third-party API compatibility issues while the caller receives a clean None-or-dict result.

## Source Files

- Implementation: See `src/erk/core/llm_json.py`
- Test coverage: See `tests/core/test_llm_json.py` (7 test cases covering all edge cases)
- Usage examples: See `src/erk/core/plan_duplicate_checker.py` and `src/erk/core/plan_relevance_checker.py`

## Cross-References

- Error boundary pattern for third-party APIs: See architecture tripwires
- Graceful degradation: Returns error message in result objects instead of raising exceptions
```

---

#### 2. Error boundary pattern for third-party APIs

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8055]

**Draft Content:**

```markdown
**adding try/except for third-party API calls (json, subprocess, requests)** → This is NOT EAFP violation. Error boundaries for third-party APIs are appropriate when catching specific exceptions (ValueError, TypeError, JSONDecodeError). Mark as "error boundary" in docstring to justify. Example: extract_json_dict() catches exceptions from json.JSONDecoder. Still prefer LBYL for our own code.
```

---

#### 3. Graceful degradation for LLM calls

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the existing architecture patterns section:

```markdown
## Graceful Degradation for LLM Calls

When LLM output is malformed, return error messages in result objects instead of raising exceptions. This allows callers to handle gracefully.

**Pattern:**
- Return `None` for parse failures (like `extract_json_dict()`)
- Return error message strings in result dataclass fields
- Never raise exceptions for malformed LLM responses

**Examples:**
- `PlanDuplicateChecker.check()` returns error message in result on parse failure
- `PlanRelevanceChecker.check()` returns error message in result on parse failure
- `extract_json_dict()` returns None instead of raising JSONDecodeError

**Rationale:** LLM responses are inherently unpredictable. Raising exceptions forces every caller to wrap in try/except. Returning structured results enables graceful degradation paths.
```

---

#### 4. Plan duplicate/relevance checker pattern update

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8055]

**Draft Content:**

```markdown
**adding LLM-based plan checks (duplicate detection, relevance assessment)** → Read [LLM JSON Parsing Reference](../reference/llm-json-parsing.md) first. Follow the pattern in `plan_duplicate_checker.py`: constructor injection with PromptExecutor, model="haiku", frozen result dataclass. JSON extraction via `extract_json_dict()` (never custom fence parsing).
```

---

## Contradiction Resolutions

No contradictions found between new insights and existing documentation. All existing JSON parsing guidance is complementary and consistent.

## Stale Documentation Cleanup

### 1. metadata-blocks.md import path notation

**Location:** `docs/learned/architecture/metadata-blocks.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `erk_shared.gateway.github.metadata.core` (uses Python import path notation)
**Cleanup Instructions:** The file exists at `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`. The doc uses Python import path instead of file path. This is documentation shorthand, not a true phantom reference. Consider changing to file path for clarity and grep-ability, or leave as-is since the import path is accurate.

---

## Prevention Insights

This was a clean implementation session with no errors encountered, indicating the new pattern successfully prevents the class of bugs caused by brittle fence-stripping.

### 1. Brittle Fence-Stripping

**What happened:** Production `erk plan duplicate-check` failed when Haiku added trailing commentary after the closing JSON fence.
**Root cause:** The old pattern assumed `fence_lines[-1]` was always the closing fence marker.
**Prevention:** Use `json.JSONDecoder.raw_decode()` which ignores everything before and after the JSON object.
**Recommendation:** TRIPWIRE - documented above as high priority item.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. extract_json_dict() for LLM output

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** Before parsing JSON from LLM output (claude --print, PromptExecutor responses)
**Warning:** ALWAYS use `extract_json_dict()` from `erk.core.llm_json`, NEVER write fence-stripping logic
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because:
1. The raw_decode() method is non-obvious - agents won't discover it independently
2. The pattern applies to ALL LLM JSON parsing across erk
3. The old approach (fence-stripping) seems reasonable until it breaks in production
4. Two modules already used the broken pattern before this PR

### 2. json.JSONDecoder.raw_decode() pattern

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before extracting JSON from unstructured text
**Warning:** Use `json.JSONDecoder.raw_decode()` instead of json.loads()
**Target doc:** `docs/learned/architecture/tripwires.md`

This is the underlying pattern that `extract_json_dict()` uses. Worth documenting separately because:
1. Agents may need to extract JSON in contexts where the erk utility isn't available
2. Understanding the underlying mechanism helps agents reason about edge cases

---

## Potential Tripwires

No items with score 2-3 identified.

---

## Additional Notes

### Reusability Assessment

The `extract_json_dict()` utility is highly reusable and likely to become a core pattern across erk. All commands that call `claude --print --output-format text` or parse JSON from LLM responses should use this utility.

### Test Coverage

The new utility has comprehensive test coverage in `tests/core/test_llm_json.py`:
- Raw JSON dict (no wrapping)
- Code fence wrapped JSON
- Trailing text after fence (the bug scenario)
- Preamble text before JSON
- Error cases (not JSON, empty string, JSON array)

The regression test `test_json_wrapped_in_code_fence_with_trailing_text` in the duplicate checker test suite captures the exact scenario that exposed the original bug.

### Session Quality

The implementation session demonstrated excellent adherence to erk patterns:
- Proper task decomposition (6 sequential tasks tracked)
- Comprehensive test coverage before refactoring
- Consistent pattern application across multiple modules
- No errors encountered (indicating good planning)
- Proper use of devrun agent for all CI operations
