---
description: Scan docs/learned/ for documents most in need of audit
context: fork
agent: general-purpose
---

# /local:audit-scan

Scan all `docs/learned/` files, score them by audit priority using heuristic signals, including indicators of prose-reality drift risk, and present a tiered report of candidates for deep audit via `/local:audit-doc`.

## Usage

```bash
/local:audit-scan                        # Scan all docs/learned/
/local:audit-scan --category planning    # Scope to a specific category
```

## Instructions

### Phase 1: Parse Arguments and Discover Documents

Parse `$ARGUMENTS` for optional `--category <name>` flag to scope the scan to `docs/learned/<name>/`.

**Discover all documents:**

1. Glob for all `.md` files in `docs/learned/` recursively (or scoped category if specified)
2. Read the first 5 lines of each file to check for auto-generated markers
3. **Skip** files whose first line starts with `<!-- AUTO-GENERATED` — these are generated index/tripwire files (e.g., `index.md`, `tripwires.md`, `tripwires-index.md`)
4. **Exclude recently audited**: Use Grep to find `last_audited` across all remaining files. Parse the date values and exclude any document whose `last_audited` date is within the last 7 days. These docs are too fresh to need re-audit.
5. Build a working list of document paths for scoring

Report: "Found X documents to scan (skipped Y auto-generated, excluded Z audited within 7 days)"

### Phase 2: Partition into Batches

Split the document list into 5 roughly equal batches using round-robin assignment by file list order. This is purely mechanical — no analysis needed.

### Phase 3: Launch 5 Parallel Scoring Agents

Generate a unique run ID for scratch storage: `audit-scan-<timestamp>` (e.g., `audit-scan-20260203-1430`).

Launch 5 Task agents in parallel, each with `subagent_type=general-purpose` and `model=haiku`.

Each agent receives:

- Its batch of doc paths
- A scratch output path: `.erk/scratch/<run-id>/batch-<N>.md`

**Per-doc signals to collect:**

- **Line count**: Total lines in the file
- **Code block count**: Number of triple-backtick sections
- **File path reference count**: Number of explicit paths matching `src/`, `packages/`, `tests/`, `.claude/`
- **Broken path check**: For up to 3 file path references per doc, check if the path exists. Record how many are broken.
- **`last_audited` field**: Whether it exists in frontmatter, and the date value if present
- **`audit_result` field**: Value if present (e.g., `clean`, `edited`)
- **`redirect_to` field**: Whether it exists in frontmatter
- **Import count**: Number of `from` or `import` statements inside code blocks
- **Behavioral claims**: Count of statements containing "returns", "raises", "does", "will", "must", "always", "never" in prose (outside code blocks)
- **Step sequences**: Count of numbered lists with 3+ items (procedural descriptions drift quickly)
- **Line number refs**: Count of `:line` or `line X` patterns (need accuracy verification)
- **Symbol refs**: Count of inline code that looks like function/class names (e.g., backtick-wrapped CamelCase or snake_case identifiers)

Each agent **writes** results to its assigned scratch file (using the Write tool, not inline return) in this format per doc:

```
path: docs/learned/category/file.md
lines: 154
code_blocks: 5
file_path_refs: 8
broken_paths: 2
last_audited: 2025-01-15 (or "none")
audit_result: clean (or "none")
has_redirect: false
import_count: 3
behavioral_claims: 12
step_sequences: 2
line_number_refs: 5
symbol_refs: 8

path: docs/learned/category/another-file.md
lines: 87
code_blocks: 2
file_path_refs: 3
broken_paths: 0
last_audited: none
audit_result: none
has_redirect: false
import_count: 1
behavioral_claims: 5
step_sequences: 0
line_number_refs: 0
symbol_refs: 3
```

**Agent prompt must include these explicit instructions:**

> For each doc, collect signals and append to your output file. Use EXACTLY this format with no variations, no extra text, no markdown headers between entries. Separate entries with a blank line. Do NOT use Python scripts, do NOT return results inline, do NOT add commentary. ONLY write the structured output file.

**Important**: Agents must use the Write tool for output, not return it inline. This prevents silent truncation for large result sets (see `agent-orchestration-safety.md`).

### Phase 4: Verify Output and Score

**Verify agent output files exist** before reading. For each batch file (`.erk/scratch/<run-id>/batch-<N>.md`), run `ls` to confirm it was written. If any file is missing, report which batch failed and stop — do not silently proceed with partial data.

Gather all agent results by reading the scratch files.

Apply this point-based scoring rubric (higher score = more urgent):

| Signal                                                          | Points | Rationale                               |
| --------------------------------------------------------------- | ------ | --------------------------------------- |
| No `last_audited` field                                         | +3     | Never been audited                      |
| `last_audited` > 30 days ago                                    | +2     | Stale audit                             |
| Line count > 200                                                | +2     | Large docs drift more                   |
| Line count > 100                                                | +1     | Medium docs                             |
| Has 3+ code blocks                                              | +2     | Code examples are drift-prone           |
| Has 5+ file path references                                     | +2     | Path references go stale                |
| Any broken path detected                                        | +3     | Already broken                          |
| Has import statements in code blocks                            | +1     | Import paths drift                      |
| Has step sequences (step_sequences > 0)                         | +1     | Procedural descriptions drift quickly   |
| High behavioral claim density (behavioral_claims / lines > 0.1) | +2     | Dense claims = more verification needed |
| Has line number references                                      | +1     | Line numbers go stale with refactoring  |
| Has `redirect_to` field                                         | -2     | Already a stub, low priority            |
| `audit_result: edited` (recently cleaned)                       | -1     | Recently maintained                     |

### Phase 5: Rank and Tier

Sort all docs by score descending. Assign tiers:

| Tier         | Score | Meaning                                     |
| ------------ | ----- | ------------------------------------------- |
| **HIGH**     | 10+   | Likely stale or broken — audit soon         |
| **MODERATE** | 6-9   | Showing age signals — audit when convenient |
| **LOW**      | 3-5   | Minor signals — audit eventually            |
| **SKIP**     | 0-2   | Recently audited or minimal risk            |

### Phase 6: Present Report

Output a structured report:

```markdown
## Doc Audit Scan Results

**Scanned:** X documents | **Skipped:** Y auto-generated files | **Excluded:** Z recently audited (within 7 days)

### HIGH Priority (X docs)

| Doc                       | Score | Lines | Key Signals                          |
| ------------------------- | ----- | ----- | ------------------------------------ |
| `planning/plan-schema.md` | 12    | 154   | no audit, 5 code blocks, broken path |

### MODERATE Priority (X docs)

| Doc | Score | Lines | Key Signals |
| --- | ----- | ----- | ----------- |

### LOW Priority (X docs)

(Summary table — same format as above)

### SKIP (X docs)

(Count and collapsed list of doc names only)

### Stats

- Never audited: X docs
- Last audited >30 days: X docs
- Broken paths detected: X docs
- Total documents with redirect stubs: X docs
- Docs with step sequences: X docs
- Total behavioral claims across all docs: X
```

Show paths relative to `docs/learned/` for brevity.

### Phase 7: Offer Actions

Use AskUserQuestion to offer:

- **"Audit top N candidates"** — run `/local:audit-doc` on the top N HIGH-priority docs in parallel, auto-selecting actions
- **"Show details for a specific doc"** — let user pick one to inspect further
- **"Export list"** — write the ranked list to `.erk/scratch/audit-scan-results.md`
- **"No action"** — just noting findings

### Phase 8: Execute Actions

Based on user choice:

- **Audit top N**: Default N to 10. Launch N parallel Task agents (using `subagent_type=general-purpose`), one per doc, each invoking `/local:audit-doc <path>` via the Skill tool. When running in batch mode from audit-scan, auto-select actions without prompting: if non-trivial issues are found, automatically choose "Apply rewrite + stamp"; if the doc is clean (no issues found), automatically choose "Mark as audited (clean)". Do not ask the user between docs — run all N in parallel.
- **Show details**: Let user specify which doc. Read it and present a quick summary: title, section headings with line counts, frontmatter fields, and first few lines of each section.
- **Export**: Write the full ranked table (all tiers) to `.erk/scratch/audit-scan-results.md` in markdown format.

## Design Principles

1. **Heuristic scoring, not LLM judgment**: Scoring is purely mechanical (line counts, path checks, frontmatter presence). This makes the scan fast, deterministic, and cheap. Deep judgment is deferred to `/local:audit-doc`.

2. **Parallel general-purpose agents with haiku**: Use 5 parallel haiku-model general-purpose agents to keep scanning fast and cost-effective. Each agent handles ~16-20 docs. General-purpose agents have Write tool access, which is required for structured output.

3. **Integration with audit-doc**: The scan feeds into the existing deep-audit command rather than duplicating its analysis. Scan = triage, audit-doc = deep analysis.

4. **Relative paths in output**: Show `category/file.md` not full paths, for readability and easy copy-paste into `/local:audit-doc`.
