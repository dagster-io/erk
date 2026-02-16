# Audit Score-6 docs/learned/ Documents

## Context

This is step 2.4 of objective #7132 ("Audit All docs/learned/ Documents"). Previous steps audited docs at score 9 (PR #7167), score 8 (PR #7169), and score 7 (PR #7186). This step audits all documents with an audit-scan heuristic score of 6.

The audit-scan scoring rubric (defined in `.claude/commands/local/audit-scan.md`) assigns points based on: no `last_audited` field (+3), `last_audited` >30 days (+2), line count >200 (+2), >100 (+1), 3+ code blocks (+2), 5+ file path refs (+2), broken paths (+3), imports (+1), step sequences (+1), high behavioral claim density (+2), line number refs (+1), `redirect_to` (-2), `audit_result: edited` (-1).

**Important**: The exact document list must be determined at implementation time by running the scoring script below, since prior audit PRs may have changed scores. At planning time, approximately 49 docs score exactly 6. The objective description says "64 docs" but this was estimated before prior audit PRs landed and shifted some scores.

## Document Discovery

Run this Python script to identify all score-6 documents at implementation time:

```python
python3 << 'PYEOF'
import os, re
from pathlib import Path
from datetime import datetime, timedelta

docs_dir = Path("docs/learned")
now = datetime.now()
thirty_days_ago = now - timedelta(days=30)

def parse_audit_date(date_str):
    date_str = date_str.strip().strip('"').strip("'")
    try:
        return datetime.strptime(date_str.replace(" PT", ""), "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(date_str.split()[0], "%Y-%m-%d")
        except ValueError:
            return None

def is_auto_generated(filepath):
    try:
        with open(filepath) as f:
            first_line = f.readline()
            return first_line.startswith("<!-- AUTO-GENERATED")
    except:
        return False

def score_doc(filepath):
    try:
        content = filepath.read_text()
    except:
        return None
    lines = content.split('\n')
    line_count = len(lines)
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    last_audited = None
    audit_result = None
    has_redirect = False
    if fm_match:
        fm = fm_match.group(1)
        la_match = re.search(r'last_audited:\s*["\']?([^"\'\n]+)', fm)
        if la_match:
            last_audited = parse_audit_date(la_match.group(1))
        ar_match = re.search(r'audit_result:\s*(\w+)', fm)
        if ar_match:
            audit_result = ar_match.group(1)
        if 'redirect_to:' in fm:
            has_redirect = True

    code_blocks = len(re.findall(r'```', content)) // 2
    file_path_refs = len(re.findall(r'(?:src/|packages/|tests/|\.claude/)\S+', content))
    in_code = False
    import_count = 0
    behavioral_claims = 0
    for line in lines:
        if line.strip().startswith('```'):
            in_code = not in_code
        elif in_code and re.match(r'\s*(from|import)\s+', line):
            import_count += 1
        elif not in_code:
            behavioral_claims += len(re.findall(r'\b(returns|raises|does|will|must|always|never)\b', line, re.IGNORECASE))

    step_sequences = 0
    numbered_run = 0
    for line in lines:
        if re.match(r'\s*\d+[\.\)]\s+', line):
            numbered_run += 1
        else:
            if numbered_run >= 3:
                step_sequences += 1
            numbered_run = 0
    if numbered_run >= 3:
        step_sequences += 1

    line_number_refs = len(re.findall(r':line|\bline \d+\b|\bL\d+\b', content))

    score = 0
    if last_audited is None:
        score += 3
    elif last_audited < thirty_days_ago:
        score += 2
    if line_count > 200:
        score += 2
    elif line_count > 100:
        score += 1
    if code_blocks >= 3:
        score += 2
    if file_path_refs >= 5:
        score += 2
    if import_count > 0:
        score += 1
    if step_sequences > 0:
        score += 1
    if line_count > 0 and (behavioral_claims / line_count) > 0.1:
        score += 2
    if line_number_refs > 0:
        score += 1
    if has_redirect:
        score -= 2
    if audit_result == "edited":
        score -= 1
    return score

results = []
for md_file in sorted(docs_dir.rglob("*.md")):
    if is_auto_generated(md_file):
        continue
    score = score_doc(md_file)
    if score == 6:
        results.append(str(md_file.relative_to(docs_dir)))

print(f"Found {len(results)} score-6 documents:")
for r in results:
    print(f"  {r}")
PYEOF
```

At planning time, these docs scored 6 (sorted by category for batching):

### Architecture (7 docs)
- `architecture/claude-cli-error-reporting.md`
- `architecture/gateway-hierarchy.md`
- `architecture/gateway-signature-migration.md`
- `architecture/optional-field-propagation.md`
- `architecture/parameter-threading-pattern.md`
- `architecture/ssh-command-execution.md`
- `architecture/state-threading-pattern.md`

### Capabilities (1 doc)
- `capabilities/adding-reviews.md`

### CI (3 docs)
- `ci/commit-squash-divergence.md`
- `ci/github-token-scopes.md`
- `ci/plan-implement-customization.md`

### Claude Code (1 doc)
- `claude-code/context-fork-feature.md`

### CLI (8 docs)
- `cli/cli-options-validation.md`
- `cli/codespace-patterns.md`
- `cli/command-organization.md`
- `cli/commands/pr-sync-divergence.md`
- `cli/commands/update-roadmap-step.md`
- `cli/dependency-injection-patterns.md`
- `cli/help-text-formatting.md`
- `cli/learn-command-conditional-pipeline.md`

### CLI / Sessions / Commands (3 docs)
- `cli/session-management.md`
- `commands/tool-restriction-safety.md`
- `configuration/config-layers.md`

### Configuration (1 doc)
- `configuration/issues-repo.md`

### Desktop-Dash (2 docs)
- `desktop-dash/forge-vite-setup.md`
- `desktop-dash/tripwires.md`

### Erk (2 docs)
- `erk/graphite-branch-setup.md`
- `erk/slot-pool-architecture.md`

### Guide (1 doc)
- `guide.md`

### Integrations (1 doc)
- `integrations/codex/codex-cli-reference.md`

### Objectives (1 doc)
- `objectives/objective-lifecycle.md`

### Planning (5 docs)
- `planning/agent-delegation.md`
- `planning/learn-plan-metadata-fields.md`
- `planning/one-shot-workflow.md`
- `planning/plan-lookup-strategy.md`
- `planning/pr-review-workflow.md`

### Planning / Review / Reference (3 docs)
- `planning/remote-implementation-idempotency.md`
- `planning/tripwires.md`
- `review/prompt-assembly.md`

### Sessions (2 docs)
- `sessions/layout.md`
- `sessions/tools.md`

### Testing (3 docs)
- `testing/cli-testing.md`
- `testing/integration-test-speed.md`
- `testing/monkeypatch-vs-fakes-decision.md`

### Testing / TUI / Textual (4 docs)
- `testing/session-log-fixtures.md`
- `textual/datatable-markup-escaping.md`
- `tui/textual-async.md`
- `tui/title-truncation-edge-cases.md`

### Reference (1 doc)
- `reference/github-actions-api.md`

## Changes

### Files to Modify

All score-6 `docs/learned/` documents identified by the discovery script above. Each document will be modified according to the audit-doc methodology:

1. **Frontmatter stamping**: Add or update `last_audited` and `audit_result` fields in YAML frontmatter
2. **Content fixes** (where needed): Fix broken file path references, replace verbatim code blocks with source pointers, correct inaccurate claims
3. **Structural cleanup** (where needed): Simplify duplicative sections, update stale directory trees or flow descriptions

### Files NOT Changing

- No source code files (`src/`, `packages/`, `tests/`) — this is documentation-only
- No auto-generated files (`index.md`, `tripwires.md`, `tripwires-index.md`)
- No files with scores other than 6
- `CHANGELOG.md` — never modify

## Implementation Details

### Prerequisites

1. Load the `learned-docs` skill first — it defines the content quality standards used by audit-doc
2. Read `.claude/commands/local/audit-doc.md` to understand the full 10-phase audit process
3. Read `docs/learned/documentation/audit-methodology.md` for the classification decision framework

### Processing Strategy

Process docs in **category batches** to maximize source code cache reuse. When multiple docs reference the same source files (e.g., architecture docs all reference `src/erk/gateway/`), audit them consecutively so you only read the source code once.

**Recommended batch order** (largest categories first):

1. **Batch 1 — CLI** (~8 docs): All reference `src/erk/cli/` patterns
2. **Batch 2 — Architecture** (~7 docs): All reference `src/erk/gateway/` and core patterns
3. **Batch 3 — Planning** (~5-8 docs): All reference planning workflows and `.impl/`
4. **Batch 4 — CI** (~3 docs): All reference `.github/workflows/`
5. **Batch 5 — Testing** (~3-4 docs): All reference `tests/` patterns
6. **Batch 6 — Sessions/TUI** (~4 docs): All reference `src/erk/tui/` and session patterns
7. **Batch 7 — Remaining** (~15-20 docs): Desktop-dash, erk, config, integrations, objectives, etc.

### Per-Document Audit Process

For each document, follow the `/local:audit-doc --auto-apply` methodology:

1. **Read the document** — Extract frontmatter, note prior audit state
2. **Extract code references** — Find all `src/`, `packages/`, `tests/`, `.claude/` paths
3. **Read referenced source** — Verify files exist, check function/class names match
4. **Verify system descriptions** — Confirm workflow descriptions match actual code behavior
5. **Classify sections** — Mark each as DUPLICATIVE, INACCURATE, DRIFT_RISK, HIGH_VALUE, CONTEXTUAL, REFERENCE_CACHE, or EXAMPLES
6. **Code block triage** — Classify code blocks as ANTI-PATTERN, CONCEPTUAL, VERBATIM, REFERENCE_TABLE, or TEMPLATE
7. **Determine verdict** — KEEP (≥50% high-value), SIMPLIFY (≥30% duplicative but salvageable), REPLACE_WITH_CODE_REFS (≥60% duplicative), or CONSIDER_DELETING (≥80% duplicative)
8. **Apply changes** based on verdict:
   - **KEEP** → Stamp frontmatter with `last_audited` and `audit_result: clean`
   - **SIMPLIFY/NEEDS_UPDATE** → Fix inaccurate content, replace verbatim code blocks with source pointers, stamp with `audit_result: edited`
   - **CONSIDER_DELETING** → Stamp as clean (don't auto-delete), note for future cleanup

### Frontmatter Stamping Format

```yaml
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: clean  # or "edited" if content was modified
```

Use the current date/time in Pacific time at the moment of auditing.

### Common Findings to Watch For

Based on prior audit rounds (score 9, 8, 7), expect these patterns:

1. **Broken file paths** — Most common. Files moved during package reorganizations (e.g., `src/erk/gateway/` → `packages/erk-shared/src/erk_shared/gateway/`)
2. **Stale directory trees** — Embedded `tree` output showing old package structure
3. **Phantom type references** — Docs mentioning classes/dataclasses that were removed or renamed
4. **Verbatim code copies** — Code blocks that duplicate actual source (violate One Code Rule)
5. **Stale workflow descriptions** — Step-by-step flows that don't match current implementation

### Key Rules

- **One Code Rule**: No reproduced source code in docs. Replace verbatim blocks with prose + source pointer. Four exceptions: data formats, third-party API patterns, anti-patterns marked WRONG, I/O examples.
- **Constants exception**: Constants and defaults in prose are HIGH VALUE, not DUPLICATIVE
- **Source pointer format**: `<!-- Source: path/to/file.py, ClassName.method_name -->` — prefer name-based over line-range
- **No collateral source code fixes**: This audit step modifies only `docs/learned/` files. If you discover stale source code (comments, docstrings), note them but don't fix in this PR.

## Verification

After all documents are audited:

1. **Frontmatter validation**: Every score-6 doc should now have `last_audited` and `audit_result` fields
2. **No broken internal links**: Run `erk docs sync` if any docs were deleted or significantly restructured
3. **Git diff review**: Verify the diff is documentation-only (no source code changes)
4. **Commit message format**: `"Audit score-6 docs/learned/ documents (#7191)"`

## Commit

Create a single commit with all audit changes:

```
Audit score-6 docs/learned/ documents (#7191)
```

This follows the pattern of prior audit PRs (#7167, #7169, #7186) which each use a single atomic commit.