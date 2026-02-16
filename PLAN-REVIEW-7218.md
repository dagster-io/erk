# Fix Tripwire Extractor Schema Drift

## Context

The `/erk:learn` pipeline's tripwire extraction step repeatedly fails because the LLM agent produces JSON that doesn't match the schema expected by `erk exec store-tripwire-candidates`. The agent definition (`.claude/agents/learn/tripwire-extractor.md`) correctly specifies the schema, but agents don't reliably follow it. Observed drift includes:

- Wrong root key: `tripwire_candidates` instead of `candidates`
- Wrong/missing fields: produces `title`, `description`, `trigger_pattern`, `check_type`, `source_files`, `priority` instead of the required `action`, `warning`, `target_doc_path`

This has been seen across repos, causing 4+ manual fix iterations per learn run.

## Root Cause

1. **learn.md prompt says "Load and follow the agent instructions in `.claude/agents/learn/tripwire-extractor.md`"** - This indirection means the agent must read a file and extract the schema. Smaller models especially fail at this.
2. **No normalization in validation** - `validate_candidates_json` does strict validation with no attempt to map common drift patterns.

## Plan

### 1. Inline the schema in learn.md's tripwire-extractor prompt

**File:** `.claude/commands/erk/learn.md` (lines ~528-546)

Replace the minimal prompt with one that includes the exact JSON schema inline, rather than relying on the agent to read `.claude/agents/learn/tripwire-extractor.md` and extract it. Keep the file reference for full instructions but include the critical schema directly:

```
prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/tripwire-extractor.md`

    Input:
    - learn_plan_path: "..."
    - gap_analysis_path: "..."
    - output_path: ...

    ## CRITICAL: Output JSON Schema

    Your output MUST be valid JSON matching this EXACT structure:

    {
      "candidates": [
        {
          "action": "the action pattern to detect (gerund form, e.g., 'editing CI template files')",
          "warning": "concise warning message (e.g., 'Verify CLI flag names match shared_options.py definitions')",
          "target_doc_path": "relative path within docs/learned/ (e.g., 'ci/template-validation.md')"
        }
      ]
    }

    - Root key MUST be "candidates" (NOT "tripwire_candidates")
    - Each candidate MUST have exactly 3 fields: action, warning, target_doc_path
    - Do NOT include fields like title, description, trigger_pattern, source_files, priority
    - If no candidates found, use: {"candidates": []}

    ## Output Routing
    CRITICAL: Write your complete output to the output_path using the Write tool.
    Your final message MUST be only: "Output written to <output_path>"
```

### 2. Add normalization in validate_candidates_json

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py`

Add a `_normalize_candidates_json` function called at the start of `validate_candidates_json` that handles common drift:

- **Root key normalization**: If `candidates` key missing but `tripwire_candidates` exists, rename it
- **Field mapping**: For each candidate object, map `description` → `warning` and `title`/`name` → `action` if the canonical fields are missing
- **Extra field stripping**: Silently ignore extra fields (already happens since we only `.get()` the three we need)
- Log a warning when normalization kicks in so we can track drift frequency

### 3. Add tests for normalization

**File:** `tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py`

Add test cases for:
- `tripwire_candidates` root key gets normalized to `candidates`
- `description` field gets mapped to `warning`
- Mixed schema (some fields canonical, some drifted)

## Files to Modify

1. `.claude/commands/erk/learn.md` (~line 528-546) - Inline schema in prompt
2. `packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py` - Add normalization
3. `tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py` - Add normalization tests

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py`
2. Run new normalization tests
3. Run ty on modified files