---
description: Scan docs/learned/ for documents most in need of audit
---

# /local:audit-scan

Scan all `docs/learned/` files, score them by audit priority using heuristic signals, and present a tiered report of candidates for deep audit via `/local:audit-doc`.

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
4. Build a working list of document paths for scoring

Report: "Found X documents to scan (skipped Y auto-generated files)"

### Phase 2: Partition into Batches

Split the document list into 5 roughly equal batches using round-robin assignment by file list order. This is purely mechanical — no analysis needed.

### Phase 3: Launch 5 Parallel Explore Agents

Launch 5 Task agents in parallel, each with `subagent_type=Explore` and `model=haiku`.

Each agent receives its batch of doc paths and collects these signals per doc:

**Per-doc signals to collect:**

- **Line count**: Total lines in the file
- **Code block count**: Number of triple-backtick sections
- **File path reference count**: Number of explicit paths matching `src/`, `packages/`, `tests/`, `.claude/`
- **Broken path check**: For up to 3 file path references per doc, check if the path exists. Record how many are broken.
- **`last_audited` field**: Whether it exists in frontmatter, and the date value if present
- **`audit_result` field**: Value if present (e.g., `clean`, `edited`)
- **`redirect_to` field**: Whether it exists in frontmatter
- **Import count**: Number of `from` or `import` statements inside code blocks

Each agent returns a structured result per doc in this format:

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
```

### Phase 4: Exclude Recently Audited, Then Score

Gather all agent results.

**Exclusion rule:** Completely exclude any document whose `last_audited` date is within the last 7 days. These docs are too fresh to need re-audit. Track the excluded count for the report.

Apply this point-based scoring rubric to remaining docs (higher score = more urgent):

| Signal                                    | Points | Rationale                     |
| ----------------------------------------- | ------ | ----------------------------- |
| No `last_audited` field                   | +3     | Never been audited            |
| `last_audited` > 30 days ago              | +2     | Stale audit                   |
| Line count > 200                          | +2     | Large docs drift more         |
| Line count > 100                          | +1     | Medium docs                   |
| Has 3+ code blocks                        | +2     | Code examples are drift-prone |
| Has 5+ file path references               | +2     | Path references go stale      |
| Any broken path detected                  | +3     | Already broken                |
| Has import statements in code blocks      | +1     | Import paths drift            |
| Has `redirect_to` field                   | -2     | Already a stub, low priority  |
| `audit_result: edited` (recently cleaned) | -1     | Recently maintained           |

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
```

Show paths relative to `docs/learned/` for brevity.

### Phase 7: Offer Actions

Use AskUserQuestion to offer:

- **"Audit top N candidates"** — run `/local:audit-doc` on the top N HIGH-priority docs sequentially, with user confirmation between each
- **"Show details for a specific doc"** — let user pick one to inspect further
- **"Export list"** — write the ranked list to `.erk/scratch/audit-scan-results.md`
- **"No action"** — just noting findings

### Phase 8: Execute Actions

Based on user choice:

- **Audit top N**: Ask user how many (default: 3). For each selected doc, invoke `/local:audit-doc <path>` via the Skill tool. After each audit completes, ask user whether to continue to the next.
- **Show details**: Let user specify which doc. Read it and present a quick summary: title, section headings with line counts, frontmatter fields, and first few lines of each section.
- **Export**: Write the full ranked table (all tiers) to `.erk/scratch/audit-scan-results.md` in markdown format.

## Design Principles

1. **Heuristic scoring, not LLM judgment**: Scoring is purely mechanical (line counts, path checks, frontmatter presence). This makes the scan fast, deterministic, and cheap. Deep judgment is deferred to `/local:audit-doc`.

2. **Parallel Explore agents with haiku**: Use 5 parallel haiku-model agents to keep scanning fast and cost-effective. Each agent handles ~16-20 docs.

3. **Integration with audit-doc**: The scan feeds into the existing deep-audit command rather than duplicating its analysis. Scan = triage, audit-doc = deep analysis.

4. **Relative paths in output**: Show `category/file.md` not full paths, for readability and easy copy-paste into `/local:audit-doc`.
