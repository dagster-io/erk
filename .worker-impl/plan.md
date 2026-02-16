# Audit 68 Score-5 docs/learned/ Documents

## Context

This is step 3.1 of objective #7132 ("Audit All docs/learned/ Documents"). The objective works through all documents by audit-scan priority score, starting with the highest. Previous steps completed:

- Step 1.1 (PR #7134): Audited 7 score-12 documents
- Step 1.2 (PR #7147): Audited 6 score-11 documents
- Step 1.3 (PR #7158): Audited 26 score-10 documents
- Step 2.1 (PR #7167): Audited 27 score-9 documents
- Step 2.2 (PR #7169): Audited 21 score-8 documents
- Step 2.3 (PR #7186): Audited 35 score-7 documents
- Step 2.4 (PR #7192): Audited 49 score-6 documents

This step audits 68 documents currently scoring 5 on the heuristic rubric (LOW priority tier, score 3-5). The original objective estimated 57 docs at this score, but intervening code changes and audits shifted some documents between score tiers. This is expected and consistent with the pattern seen in prior steps.

The audit-scan scoring rubric (defined in `.claude/commands/local/audit-scan.md`) assigns points based on: missing audit metadata (+3), stale audit >30 days (+2), large line count (+1/+2), code blocks (+2), file path references (+2), broken paths (+3), imports (+1), step sequences (+1), behavioral claim density (+2), line number references (+1), with deductions for redirects (-2) and recently-edited status (-1).

**Batch size note:** 68 documents is a large batch. The implementer should work through them in category batches for efficiency since documents in the same category often reference similar source files. Process categories sequentially to prevent collateral fix conflicts.

## What This Plan Does

For each of the 68 documents listed below:

1. **Read the document** and all source code files it references
2. **Verify accuracy** — check that file paths exist, code references match reality, system descriptions are correct
3. **Classify content** — identify HIGH VALUE, DUPLICATIVE, INACCURATE, and DRIFT RISK sections
4. **Apply fixes** if needed — update broken paths, fix inaccurate claims, remove duplicative content
5. **Stamp frontmatter** with `last_audited` and `audit_result` fields

### Audit Stamp Format

For clean documents (no issues found):
```yaml
last_audited: "2026-02-16 HH:MM PT"
audit_result: clean
```

For documents that required edits:
```yaml
last_audited: "2026-02-16 HH:MM PT"
audit_result: edited
```

The timestamp should use the actual time when auditing completes, in Pacific Time.

### Methodology Reference

Follow the audit methodology in `docs/learned/documentation/audit-methodology.md`:
- Verify claims against source code, not other documentation
- Constants and defaults in prose are HIGH VALUE, not duplicative
- Source pointers should target stable interfaces (ABCs, schemas), not volatile implementation
- After any deletions, run `erk docs sync` to fix cross-references

The full executable audit process is defined in `.claude/commands/local/audit-doc.md`.

## Documents to Audit (68 docs, grouped by category)

### Architecture (22 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 1 | `architecture/callback-progress-pattern.md` | 84 | never audited, 3 code blocks |
| 2 | `architecture/claude-cli-progress.md` | 191 | 4 code blocks, 7 path refs |
| 3 | `architecture/cli-binary-ops-pattern.md` | 153 | 4 code blocks, 7 steps |
| 4 | `architecture/command-boundaries.md` | 109 | never audited, 9 steps |
| 5 | `architecture/context-efficiency.md` | 63 | never audited, 4 code blocks |
| 6 | `architecture/defense-in-depth-enforcement.md` | 142 | never audited, 8 steps, 6 claims |
| 7 | `architecture/github-api-retry-mechanism.md` | 153 | 3 code blocks, 4 steps |
| 8 | `architecture/github-cli-quirks.md` | 73 | never audited, 3 code blocks |
| 9 | `architecture/github-pr-linkage-api.md` | 146 | 3 code blocks, 5 path refs |
| 10 | `architecture/graphite-cache-invalidation.md` | 111 | never audited, 3 steps |
| 11 | `architecture/issue-reference-flow.md` | 117 | never audited, 4 steps |
| 12 | `architecture/metadata-archival-pattern.md` | 139 | 3 code blocks, 5 path refs, 10 claims |
| 13 | `architecture/not-found-sentinel.md` | 140 | 3 code blocks, 8 steps |
| 14 | `architecture/phase-zero-detection-pattern.md` | 238 | 7 code blocks, 14 steps |
| 15 | `architecture/pipeline-transformation-patterns.md` | 95 | never audited, 5 code blocks |
| 16 | `architecture/pr-finalization-paths.md` | 39 | never audited, 5 claims |
| 17 | `architecture/prompt-executor-patterns.md` | 195 | 6 code blocks, 11 path refs |
| 18 | `architecture/protocol-vs-abc.md` | 489 | 14 code blocks, 7 steps, 14 claims |
| 19 | `architecture/state-derivation-pattern.md` | 203 | 6 code blocks, 13 steps |
| 20 | `architecture/symlink-validation-pattern.md` | 53 | never audited, 3 steps |
| 21 | `architecture/typescript-multi-config.md` | 111 | 5 code blocks, 14 path refs |
| 22 | `architecture/validation-patterns.md` | 69 | never audited, 11 path refs |

### CI (6 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 23 | `ci/composite-action-patterns.md` | 258 | 6 code blocks, 10 steps, 12 claims |
| 24 | `ci/exec-script-environment-requirements.md` | 99 | never audited, 4 code blocks |
| 25 | `ci/github-actions-label-queries.md` | 101 | never audited, 6 steps, 7 claims |
| 26 | `ci/github-actions-output-patterns.md` | 277 | 12 code blocks, 6 steps |
| 27 | `ci/github-cli-comment-patterns.md` | 106 | never audited, 3 steps |
| 28 | `ci/tripwires.md` | 92 | never audited, 19 claims |

### CLI (7 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 29 | `cli/cli-options-validation.md` | 110 | 7 path refs, 13 claims |
| 30 | `cli/command-group-structure.md` | 95 | 3 code blocks, 13 path refs |
| 31 | `cli/erkdesk-makefile-targets.md` | 114 | never audited, 9 steps |
| 32 | `cli/exec-command-patterns.md` | 159 | 4 code blocks, 5 path refs, 14 steps |
| 33 | `cli/exec-script-schema-patterns.md` | 119 | 4 code blocks, 14 path refs |
| 34 | `cli/optional-arguments.md` | 104 | 3 code blocks, 4 steps |
| 35 | `cli/session-management.md` | 85 | 5 path refs, 12 claims |

### Capabilities (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 36 | `capabilities/bundled-skills.md` | 78 | never audited, 8 path refs |
| 37 | `capabilities/tripwires.md` | 36 | never audited, 6 claims |

### Desktop-Dash (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 38 | `desktop-dash/defensive-bounds-handling.md` | 51 | never audited, 6 claims |

### Documentation (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 39 | `documentation/divio-documentation-system.md` | 144 | never audited, 3 steps |
| 40 | `documentation/tripwires.md` | 64 | never audited, 8 claims |

### Erk (3 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 41 | `erk/branch-cleanup.md` | 233 | 15 code blocks, 6 steps |
| 42 | `erk/pr-address-workflows.md` | 159 | never audited, 16 steps, 5 claims |
| 43 | `erk/pr-commands.md` | 69 | never audited, 10 path refs |

### Integrations (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 44 | `integrations/codex/codex-jsonl-format.md` | 189 | 4 code blocks, 11 path refs |
| 45 | `integrations/tripwires.md` | 50 | never audited, 7 claims |

### Objectives (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 46 | `objectives/roadmap-status-system.md` | 94 | never audited, 6 path refs, 6 claims |
| 47 | `objectives/tripwires.md` | 66 | never audited, 10 claims |

### Planning (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 48 | `planning/plan-backend-migration.md` | 158 | 7 code blocks, 10 path refs |
| 49 | `planning/tripwire-worthiness-criteria.md` | 156 | never audited, 8 steps |

### PR Operations (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 50 | `pr-operations/pr-creation-patterns.md` | 65 | never audited, 5 path refs |
| 51 | `pr-operations/stub-pr-workflow-link.md` | 60 | never audited, 5 path refs |

### Sessions (4 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 52 | `sessions/context-optimization.md` | 111 | never audited, 9 steps |
| 53 | `sessions/discovery-fallback.md` | 96 | never audited, 7 path refs |
| 54 | `sessions/preprocessing.md` | 203 | 8 code blocks, 7 steps |
| 55 | `sessions/tripwires.md` | 34 | never audited, 7 claims |

### Testing (3 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 56 | `testing/import-conflict-resolution.md` | 130 | 9 code blocks, 8 steps |
| 57 | `testing/mock-elimination.md` | 154 | 7 code blocks, 11 steps |
| 58 | `testing/tripwires.md` | 100 | never audited, 7 path refs, 10 claims |

### Textual (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 59 | `textual/quirks.md` | 225 | 11 code blocks, 7 steps |

### TUI (4 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 60 | `tui/command-execution.md` | 190 | 4 code blocks, 3 steps |
| 61 | `tui/dual-handler-pattern.md` | 64 | never audited, 6 path refs |
| 62 | `tui/plan-row-data.md` | 188 | 7 code blocks, 20 claims |
| 63 | `tui/tripwires.md` | 44 | never audited, 5 claims |

### Workflows (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 64 | `workflows/one-shot-workflow.md` | 126 | never audited, 20 steps |

### Changelog (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 65 | `changelog/tripwires.md` | 20 | never audited, 4 claims |

### Reference (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 66 | `reference/tripwires.md` | 38 | never audited, 7 claims |

### Root-Level (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 67 | `tripwires-index.md` | 45 | never audited, 7 path refs |
| 68 | `universal-tripwires.md` | 46 | never audited, 5 claims |

## Implementation Strategy

### Batch Processing Order

Process categories in this order (largest first to front-load the heaviest work, then group related categories):

1. **Architecture** (22 docs) — Largest batch. Many docs reference `src/erk/` source files. Read referenced source files before auditing to build context.
2. **CLI** (7 docs) — References `src/erk/cli/` heavily. Process after architecture since some docs cross-reference.
3. **CI** (6 docs) — References `.github/workflows/` and `src/erk/cli/commands/exec/`. Independent from CLI batch.
4. **Sessions** (4 docs) — References session-related source files.
5. **TUI** (4 docs) — References `src/erk/tui/`.
6. **Testing** (3 docs) — References `tests/` patterns.
7. **Erk** (3 docs) — General erk workflow docs.
8. **Remaining categories** (19 docs across 11 categories) — Process all smaller batches (capabilities, changelog, desktop-dash, documentation, integrations, objectives, planning, pr-operations, reference, textual, workflows, root).

### Per-Document Audit Process

For each document:

1. **Read the document** fully
2. **Extract all source code references** — file paths, function names, class names, import paths
3. **Verify file paths exist** — check every `src/`, `tests/`, `.claude/`, `packages/` path reference
4. **Read referenced source files** — verify that function signatures, class definitions, and behavior descriptions match actual code
5. **Check for phantom types** — verify any referenced classes, dataclasses, or enums actually exist
6. **Classify each section** as HIGH VALUE, CONTEXTUAL, DUPLICATIVE, INACCURATE, or DRIFT RISK
7. **Apply verdict**:
   - If all content is accurate: stamp as `audit_result: clean`
   - If fixes needed: apply fixes, stamp as `audit_result: edited`
   - If document is >=80% duplicative with no high-value: flag for deletion consideration (but do not delete without explicit approval)
8. **Add/update frontmatter** with `last_audited` and `audit_result`

### Tripwires Files

Many score-5 documents are per-category `tripwires.md` files (13 of 68). These contain behavioral rules with MUST/NEVER/FORBIDDEN keywords. For these:

- Verify each tripwire's `action` pattern still matches real editing scenarios
- Verify each tripwire's `warning` text is accurate against current code
- Check that referenced file paths in warnings still exist
- Stamp with audit metadata

### Discovery Script

To identify the exact documents at implementation time (scores may shift slightly if intervening PRs land), use this discovery command:

```bash
python3 -c "
import re
from pathlib import Path
from datetime import datetime

docs = Path('docs/learned')
today = datetime(2026, 2, 16)

def extract_fm(content):
    fm = {}
    if not content.startswith('---\n'):
        return fm
    m = re.search(r'\n---\n', content[4:])
    if not m:
        return fm
    yaml = content[4:4 + m.start()]
    for line in yaml.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm

def score_doc(path):
    content = path.read_text()
    if content.startswith('<!-- AUTO-GENERATED'):
        return -1
    fm = extract_fm(content)
    lc = content.count('\n') + 1
    s = 0
    la = fm.get('last_audited', '').strip()
    if not la:
        s += 3
    cb = content.count('\x60\x60\x60') // 2
    if cb >= 3: s += 2
    prs = len(re.findall(r'src/|packages/|tests/|\.claude/', content))
    if prs >= 5: s += 2
    if lc > 200: s += 2
    elif lc > 100: s += 1
    in_cb = False
    for line in content.split('\n'):
        if line.startswith('\x60\x60\x60'):
            in_cb = not in_cb
        elif in_cb and (line.strip().startswith('import ') or line.strip().startswith('from ')):
            s += 1; break
    sp = any(re.search(r'^\d+\.\s|[Ss]tep\s+\d+', l) for l in content.split('\n'))
    if sp: s += 1
    kw = ['MUST', 'SHOULD', 'REQUIRED', 'FORBIDDEN', 'NEVER', 'ALWAYS']
    claims = sum(len(re.findall(r'\b' + w + r'\b', content, re.I)) for w in kw)
    if lc > 0 and claims / lc > 0.1: s += 2
    if re.search(r'\bline\s+\d+\b|\bL\d+\b|:\d+:', content, re.I): s += 1
    if 'redirect_to' in fm: s -= 2
    if fm.get('audit_result', '').strip() == 'edited': s -= 1
    return s

for f in sorted(docs.rglob('*.md')):
    s = score_doc(f)
    if s == 5:
        print(str(f.relative_to(docs)))
"
```

If the count differs significantly from 68 (e.g., by more than 10), include any docs that score 4 or 6 that were in the original list above, to ensure comprehensive coverage.

## Files NOT Changing

- **Source code files** (`src/`, `tests/`, `.github/`) — This is a documentation-only audit. Source code is read for verification but never modified.
- **Auto-generated files** (`docs/learned/index.md`, `docs/learned/tripwires-index.md`, per-category `index.md`) — These are regenerated by `erk docs sync`.
- **CHANGELOG.md** — Never modify directly.
- **`.claude/` configuration** — Commands, skills, and hooks are not modified.

## Verification

After all documents are audited:

1. **Run `erk docs sync`** to regenerate index files and fix any cross-references broken by edits
2. **Verify no regressions** — Run `python3 -m pytest tests/unit/agent_docs/ -x` via devrun to ensure frontmatter validation passes
3. **Count check** — Verify that all 68 target documents now have `last_audited` fields:
   ```bash
   grep -rl "last_audited" docs/learned/ | wc -l
   ```
   This count should be at least 309 + 68 = 377 (current audited count + this batch)
4. **Score check** — Re-run the discovery script above. All 68 documents should now score 0-2 (SKIP tier) due to fresh `last_audited` dates.