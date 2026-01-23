# Plan: Consolidate Frontmatter Parsing

> **Replans:** #5243

## What Changed Since Original Plan

- **No implementation done**: The original plan from January 19th was never implemented
- Both `review/parsing.py` and `agent_docs/operations.py` still have independent frontmatter parsing

## Investigation Findings

### Corrections to Original Plan

1. **Return signature mismatch**: Original plan proposed unified `FrontmatterParseResult` with `body` field, but agent_docs callers never use body text. The shared API should make body optional.

2. **Error semantics differ**: Review system distinguishes "no frontmatter" from "non-dict YAML" (important for validation messaging). Agent docs treats both as same error. Shared module should preserve the richer error semantics.

### Additional Details Discovered

| Aspect | Review System | Agent Docs |
|--------|---------------|------------|
| Library | `frontmatter` package | regex + `yaml.safe_load()` |
| Returns body | Yes (needed) | No |
| Error granularity | High (3 cases) | Low (2 cases) |

## Implementation Steps

### 1. Create shared frontmatter module

**File:** `src/erk/core/frontmatter.py` (~50 lines)

```python
@dataclass(frozen=True)
class FrontmatterParseResult:
    metadata: dict[str, object] | None
    body: str  # Content after frontmatter (always populated)
    error: str | None

    @property
    def is_valid(self) -> bool:
        return self.metadata is not None

def parse_markdown_frontmatter(content: str) -> FrontmatterParseResult:
    """Parse YAML frontmatter from markdown content.

    Uses python-frontmatter library for robust parsing.
    Distinguishes: no frontmatter, invalid YAML, non-dict YAML.
    """
```

Key behaviors:
- Uses `frontmatter` library (already a dependency)
- Returns body text (callers can ignore if not needed)
- Preserves error granularity from review system

### 2. Update review/parsing.py

- Remove `parse_frontmatter()` function (lines 30-60)
- Import `parse_markdown_frontmatter` from `erk.core.frontmatter`
- Update `parse_review_file()` to use new function
- Net change: ~-25 lines

### 3. Update agent_docs/operations.py

- Remove `parse_frontmatter()` function (lines 87-108)
- Remove `FRONTMATTER_PATTERN` constant (line 26)
- Import `parse_markdown_frontmatter` from `erk.core.frontmatter`
- Update `validate_agent_doc_file()` to use new function (ignore body)
- Net change: ~-20 lines

### 4. Create unit tests for shared module

**File:** `tests/unit/core/test_frontmatter.py` (~70 lines)

Test cases:
- Valid frontmatter with body
- No frontmatter (content without `---`)
- Invalid YAML syntax
- Non-dict YAML (list, scalar)
- Empty frontmatter block
- Frontmatter with complex nested structures

### 5. Ensure existing tests pass

No changes needed to existing test files - they test at the validation layer, not the parsing layer.

## Files to Modify

| File | Action |
|------|--------|
| `src/erk/core/frontmatter.py` | Create |
| `tests/unit/core/test_frontmatter.py` | Create |
| `src/erk/review/parsing.py` | Edit (remove `parse_frontmatter`) |
| `src/erk/agent_docs/operations.py` | Edit (remove `parse_frontmatter`, `FRONTMATTER_PATTERN`) |

## Not In Scope

- Converting Agent Docs to Pydantic validation
- Consolidating `ValidationResult` types (domain-specific)
- Changing `metadata_blocks.py` (GitHub comments, not markdown files)

## Verification

1. `uv run pytest tests/unit/core/test_frontmatter.py` - new tests pass
2. `uv run pytest tests/unit/review/test_parsing.py` - existing tests pass
3. `uv run pytest tests/core/foundation/test_agent_frontmatter.py` - agent tests pass
4. `erk docs validate` - agent docs validation works
5. `uv run ty check src/erk/core/frontmatter.py src/erk/review/parsing.py src/erk/agent_docs/operations.py` - type checking passes