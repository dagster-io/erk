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

### 2. Create `erk exec normalize-tripwire-candidates` command

**New file:** `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py`

Create a standalone exec command that normalizes agent-produced tripwire JSON before it reaches `store-tripwire-candidates`. This keeps `validate_candidates_json` strict (validation only) and puts the lossy normalization in its own exec script.

```bash
erk exec normalize-tripwire-candidates --candidates-file <path>
```

The command reads the JSON file, normalizes it in-place, and writes back. Normalization rules:

- **Root key normalization**: If `candidates` key missing but `tripwire_candidates` exists, rename it
- **Field mapping**: For each candidate object, map `description` → `warning` and `title`/`name` → `action` if the canonical fields are missing
- **Extra field stripping**: Only keep `action`, `warning`, `target_doc_path` per candidate
- Output JSON result: `{"success": true, "normalized": true/false, "count": N}` (normalized=true if any fixes were applied)

The `learn.md` command calls this between the tripwire extractor agent and `store-tripwire-candidates`:

```bash
erk exec normalize-tripwire-candidates \
    --candidates-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json

erk exec store-tripwire-candidates \
    --issue <issue> \
    --candidates-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json
```

### 3. Add tests for the normalize command

**New file:** `tests/unit/cli/commands/exec/scripts/test_normalize_tripwire_candidates.py`

Add test cases for:
- `tripwire_candidates` root key gets normalized to `candidates`
- `description` field gets mapped to `warning`
- `title` field gets mapped to `action`
- Mixed schema (some fields canonical, some drifted)
- Already-correct JSON passes through unchanged (`normalized: false`)
- Extra fields are stripped

### 4. Update learn.md to call normalize before store

**File:** `.claude/commands/erk/learn.md` (Step 8)

Add the `normalize-tripwire-candidates` call before `store-tripwire-candidates`.

## Files to Modify

1. `.claude/commands/erk/learn.md` (~line 528-546) - Inline schema in prompt
2. `.claude/commands/erk/learn.md` (Step 8) - Add normalize call before store
3. `src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py` - New exec command
4. `tests/unit/cli/commands/exec/scripts/test_normalize_tripwire_candidates.py` - Tests for normalize command

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py`
2. Run new normalization tests
3. Run ty on modified files