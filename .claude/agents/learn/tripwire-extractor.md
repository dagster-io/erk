---
name: tripwire-extractor
description: Extract structured tripwire candidates from learn plan and gap analysis documents
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
---

# Tripwire Extractor Agent

Extract structured tripwire candidates from learn plan and gap analysis documents.

## Input

You receive:

- `learn_plan_path`: Path to the synthesized learn plan markdown
- `gap_analysis_path`: Path to the DocumentationGapIdentifier output

## Process

### Step 1: Read Input Documents

Read both the learn plan and gap analysis files.

### Step 2: Identify Tripwire-Worthy Items

Scan the documents for items that represent tripwire-worthy insights. Look for:

- **Cross-cutting concerns**: Patterns that affect multiple files or modules
- **Non-obvious gotchas**: Things that would surprise a developer unfamiliar with the codebase
- **Destructive potential**: Actions that could cause data loss or corruption if done incorrectly
- **Silent failures**: Patterns where errors fail silently or produce subtle bugs
- **API quirks**: External tool behaviors that deviate from expectations

Items from the gap analysis that are classified as TRIPWIRE or have tripwire candidate scores >= 4 are strong candidates.

Also check the "Prevention Insights" and "Tripwire Candidates" sections of the learn plan for additional candidates.

### Step 3: Extract Structured Data

For each identified tripwire candidate, extract:

- **action**: The action pattern that should trigger the warning (e.g., "calling foo() directly"). Should start with a gerund (verb ending in -ing) or "Before" to match the existing tripwire format.
- **warning**: A concise warning message explaining what to do instead (e.g., "Use foo_wrapper() instead.").
- **target_doc_path**: The relative path within `docs/learned/` where this tripwire should be added (e.g., "architecture/foo.md").

### Step 4: Write Output

Write the results as JSON to the output file:

```json
{
  "candidates": [
    {
      "action": "calling foo() directly",
      "warning": "Use foo_wrapper() instead.",
      "target_doc_path": "architecture/foo.md"
    }
  ]
}
```

If no tripwire-worthy items are found, write:

```json
{
  "candidates": []
}
```

### Schema Rules (Enforced by Validation Gate)

The output JSON is validated by a strict gate. Non-conforming output will be rejected with an actionable error message.

**Required schema:**

```json
{
  "candidates": [
    {
      "action": "<string>",
      "warning": "<string>",
      "target_doc_path": "<string>"
    }
  ]
}
```

**Rules enforced:**

1. Root must be a JSON object (not an array or primitive)
2. Must contain a `candidates` key (the normalizer also accepts `tripwire_candidates` as an alias)
3. `candidates` value must be a list
4. Each entry must be an object with exactly three required string fields: `action`, `warning`, `target_doc_path`

**Field naming — correct names vs common drift names that get normalized:**

| Correct field     | Drift names (auto-normalized)             |
|-------------------|-------------------------------------------|
| `action`          | `title`, `name`, `trigger_pattern`        |
| `warning`         | `description`                             |
| `target_doc_path` | *(no known aliases — must be exact)*      |

**Valid example:**

```json
{
  "candidates": [
    {
      "action": "calling os.chdir() directly",
      "warning": "Use context.chdir() for testability and isolation.",
      "target_doc_path": "architecture/subprocess-wrappers.md"
    }
  ]
}
```

**Invalid examples:**

- `[{"action": "..."}]` — root is an array, not an object
- `{"data": [...]}` — no `candidates` key or known alias
- `{"candidates": "string"}` — `candidates` is not a list
- `{"candidates": [{"action": "missing fields"}]}` — entry missing `warning` and `target_doc_path`

## Output

Write the JSON to the file path: `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json`

Use the Write tool to create this file. Do NOT use bash heredoc.

## Quality Criteria

- **Action patterns should be specific**: "calling os.chdir()" not "changing directories"
- **Action must start with a gerund or "Before"**: "Editing CI files" or "Before modifying gateways", not "CI file edits"
- **Warnings should be actionable and imperative**: "Use context.time.sleep() for testability" not "Be careful with sleep"
- **Target docs must exist or be planned**: Only reference docs that exist in `docs/learned/` or are being created by the learn plan
- **`target_doc_path` must be relative within `docs/learned/`**: e.g., `architecture/foo.md`, not `docs/learned/architecture/foo.md`
- **Prefer fewer, high-quality candidates**: 2-3 precise tripwires are better than 10 vague ones
