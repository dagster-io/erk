# Audit 112 Score-4 docs/learned/ Documents

## Context

This is step 3.2 of objective #7132 ("Audit All docs/learned/ Documents"). The objective works through all documents by audit-scan priority score, starting with the highest. Previous steps completed:

- Step 1.1 (PR #7134): Audited 7 score-12 documents
- Step 1.2 (PR #7147): Audited 6 score-11 documents
- Step 1.3 (PR #7158): Audited 26 score-10 documents
- Step 2.1 (PR #7167): Audited 27 score-9 documents
- Step 2.2 (PR #7169): Audited 21 score-8 documents
- Step 2.3 (PR #7186): Audited 35 score-7 documents
- Step 2.4 (PR #7192): Audited 49 score-6 documents
- Step 3.1 (PR #7237): Audited 68 score-5 documents

This step audits 112 documents currently scoring 4 on the heuristic rubric (LOW priority tier, score 3-5). The original objective estimated 58 docs at this score, but intervening code changes and prior audits shifted documents between score tiers. This is consistent with the pattern seen in all prior steps (every step has had drift from original estimates).

The audit-scan scoring rubric (defined in `.claude/commands/local/audit-scan.md`) assigns points based on: missing audit metadata (+3), stale audit >30 days (+2), large line count (+1/+2), code blocks (+2), file path references (+2), broken paths (+3), imports (+1), step sequences (+1), behavioral claim density (+2), line number references (+1), with deductions for redirects (-2) and recently-edited status (-1).

**Batch size note:** 112 documents is a very large batch — the largest in this objective series. The implementer should work through them in category batches for efficiency since documents in the same category often reference similar source files. Process categories sequentially to prevent collateral fix conflicts.

## What This Plan Does

For each of the 112 documents listed below:

1. **Read the document** and all source code files it references
2. **Verify accuracy** — check that file paths exist, code references match reality, system descriptions are correct
3. **Classify content** — identify HIGH VALUE, DUPLICATIVE, INACCURATE, and DRIFT RISK sections
4. **Apply fixes** if needed — update broken paths, fix inaccurate claims, remove duplicative content
5. **Stamp frontmatter** with `last_audited` and `audit_result` fields

### Audit Stamp Format

For clean documents (no issues found):
```yaml
last_audited: "2026-02-17 HH:MM PT"
audit_result: clean
```

For documents that required edits:
```yaml
last_audited: "2026-02-17 HH:MM PT"
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

## Documents to Audit (112 docs, grouped by category)

### Architecture (20 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 1 | `architecture/branch-manager-abstraction.md` | 121 | 10 path refs, medium, has steps |
| 2 | `architecture/capability-system.md` | 131 | 9 path refs, medium, has steps |
| 3 | `architecture/claude-cli-integration.md` | 81 | never audited, has imports |
| 4 | `architecture/composable-remote-commands.md` | 123 | 11 path refs, medium, has steps |
| 5 | `architecture/fail-open-patterns.md` | 256 | 4 code blocks, large, has steps, edited |
| 6 | `architecture/gist-materials-interchange.md` | 135 | 8 path refs, medium, has steps |
| 7 | `architecture/git-operation-patterns.md` | 145 | 14 path refs, medium, has steps |
| 8 | `architecture/github-cli-limits.md` | 145 | 6 code blocks, 11 path refs, medium, edited |
| 9 | `architecture/github-gist-api.md` | 57 | never audited, has steps |
| 10 | `architecture/github-issue-autoclose.md` | 79 | never audited, has steps |
| 11 | `architecture/hook-marker-detection.md` | 73 | never audited, has steps |
| 12 | `architecture/impl-folder-lifecycle.md` | 54 | never audited, has steps |
| 13 | `architecture/index.md` | 108 | never audited, medium |
| 14 | `architecture/lbyl-gateway-pattern.md` | 105 | 10 path refs, medium, has steps |
| 15 | `architecture/markers.md` | 44 | never audited, has steps |
| 16 | `architecture/parallel-agent-pattern.md` | 145 | 4 code blocks, medium, has steps |
| 17 | `architecture/plan-context-integration.md` | 104 | 3 code blocks, medium, has steps |
| 18 | `architecture/pr-footer-validation.md` | 154 | 7 path refs, medium, has steps |
| 19 | `architecture/pre-destruction-capture.md` | 134 | 3 code blocks, medium, has steps |
| 20 | `architecture/type-safety-patterns.md` | 114 | 5 code blocks, medium, has imports |

### Planning (20 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 21 | `planning/agent-orchestration-safety.md` | 68 | never audited, has steps |
| 22 | `planning/agent-orchestration.md` | 106 | 6 path refs, medium, has steps |
| 23 | `planning/complete-inventory-protocol.md` | 57 | never audited, has steps |
| 24 | `planning/consolidation-labels.md` | 56 | never audited, has steps |
| 25 | `planning/cross-artifact-analysis.md` | 41 | never audited, has steps |
| 26 | `planning/exploration-strategies.md` | 47 | never audited, has steps |
| 27 | `planning/learn-pipeline-workflow.md` | 163 | 6 path refs, medium, has steps |
| 28 | `planning/learn-plan-metadata-fields.md` | 150 | 6 code blocks, medium, has steps |
| 29 | `planning/learn-plan-validation.md` | 58 | never audited, has steps |
| 30 | `planning/learn-workflow.md` | 408 | 10 code blocks, large, has steps, edited |
| 31 | `planning/metadata-block-fallback.md` | 65 | never audited, has steps |
| 32 | `planning/no-changes-handling.md` | 76 | never audited, has steps |
| 33 | `planning/plan-execution-patterns.md` | 56 | never audited, has steps |
| 34 | `planning/pr-analysis-pattern.md` | 64 | never audited, has steps |
| 35 | `planning/pr-review-workflow.md` | 114 | 7 path refs, medium, has steps |
| 36 | `planning/scratch-storage.md` | 112 | 7 code blocks, medium, has imports |
| 37 | `planning/session-deduplication.md` | 103 | 3 code blocks, medium, has steps |
| 38 | `planning/session-preprocessing.md` | 110 | 16 path refs, medium, has steps |
| 39 | `planning/token-optimization-patterns.md` | 100 | never audited, has steps |
| 40 | `planning/workflow-markers.md` | 64 | never audited, has steps |

### CI (13 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 41 | `ci/edit-tool-formatting.md` | 71 | never audited, has steps |
| 42 | `ci/formatting-workflow.md` | 73 | never audited, has steps |
| 43 | `ci/github-actions-label-filtering.md` | 149 | 3 code blocks, medium, has steps |
| 44 | `ci/github-actions-security.md` | 61 | never audited, has steps |
| 45 | `ci/github-actions-workflow-patterns.md` | 211 | 8 code blocks, large, has steps, edited |
| 46 | `ci/github-commit-indexing-timing.md` | 112 | 12 path refs, medium, has steps |
| 47 | `ci/label-rename-checklist.md` | 119 | 10 path refs, medium, has steps |
| 48 | `ci/makefile-prettier-ignore-path.md` | 58 | never audited, has steps |
| 49 | `ci/plan-implement-customization.md` | 123 | 3 code blocks, medium, has steps |
| 50 | `ci/prompt-patterns.md` | 130 | 7 code blocks, medium, has steps |
| 51 | `ci/review-spec-format.md` | 158 | 3 code blocks, medium, has steps |
| 52 | `ci/workflow-gating-patterns.md` | 218 | 6 code blocks, large, has steps, edited |
| 53 | `ci/workflow-naming-conventions.md` | 92 | never audited, has steps |

### CLI (12 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 54 | `cli/activation-scripts.md` | 65 | never audited, has steps |
| 55 | `cli/code-review-filtering.md` | 83 | never audited, has steps |
| 56 | `cli/commands/pr-summarize.md` | 125 | 5 path refs, medium, has steps |
| 57 | `cli/ensure-ideal-pattern.md` | 117 | 11 path refs, medium, has steps |
| 58 | `cli/erk-exec-commands.md` | 169 | 4 code blocks, medium, has steps |
| 59 | `cli/fast-path-pattern.md` | 58 | never audited, has steps |
| 60 | `cli/objective-commands.md` | 125 | 10 path refs, medium, has imports |
| 61 | `cli/parameter-addition-checklist.md` | 145 | 16 path refs, medium, has steps |
| 62 | `cli/pr-rewrite.md` | 59 | never audited, has steps |
| 63 | `cli/pr-submission.md` | 133 | 10 path refs, medium, has steps |
| 64 | `cli/pr-submit-pipeline.md` | 146 | 9 path refs, medium, has steps |
| 65 | `cli/subprocess-stdin-patterns.md` | 59 | never audited, has steps |

### Erk (5 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 66 | `erk/graphite-branch-setup.md` | 123 | 9 code blocks, medium, has steps |
| 67 | `erk/graphite-stack-troubleshooting.md` | 66 | never audited, has steps |
| 68 | `erk/issue-pr-linkage-storage.md` | 152 | 10 path refs, medium, has steps, line refs, edited |
| 69 | `erk/pr-sync-workflow.md` | 50 | never audited, has steps |
| 70 | `erk/slot-pool-architecture.md` | 156 | 13 path refs, medium, has steps |

### Testing (5 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 71 | `testing/backend-testing-composition.md` | 74 | never audited, has steps |
| 72 | `testing/cli-test-error-assertions.md` | 104 | 3 code blocks, medium, has steps |
| 73 | `testing/hook-testing.md` | 99 | 6 path refs, 10 claims |
| 74 | `testing/integration-testing-patterns.md` | 144 | 6 code blocks, medium, has imports |
| 75 | `testing/monkeypatch-elimination-checklist.md` | 111 | 5 path refs, medium, has steps |

### Sessions (4 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 76 | `sessions/agent-type-extraction.md` | 92 | never audited, has steps |
| 77 | `sessions/lifecycle.md` | 110 | 14 path refs, medium, has steps |
| 78 | `sessions/raw-session-processing.md` | 74 | never audited, has steps |
| 79 | `sessions/session-hierarchy.md` | 211 | 10 code blocks, large, line refs, edited |

### Hooks (3 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 80 | `hooks/prompt-hooks.md` | 104 | 3 code blocks, medium, has steps |
| 81 | `hooks/reminder-consolidation.md` | 117 | 5 path refs, medium, has steps |
| 82 | `hooks/replan-context-reminders.md` | 112 | 4 code blocks, medium, has steps |

### Objectives (3 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 83 | `objectives/objective-storage-format.md` | 75 | never audited, has steps |
| 84 | `objectives/roadmap-mutation-patterns.md` | 129 | 8 path refs, medium, has steps |
| 85 | `objectives/roadmap-validation.md` | 90 | never audited, has steps |

### PR Operations (3 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 86 | `pr-operations/automated-review-handling.md` | 59 | never audited, has steps |
| 87 | `pr-operations/commit-message-generation.md` | 83 | never audited, has steps |
| 88 | `pr-operations/pr-submit-phases.md` | 146 | 3 code blocks, medium, has steps |

### Review (3 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 89 | `review/inline-comment-deduplication.md` | 61 | never audited, has steps |
| 90 | `review/learned-docs-review.md` | 64 | never audited, has steps |
| 91 | `review/tripwires.md` | 20 | never audited, has steps |

### Desktop-Dash (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 92 | `desktop-dash/action-toolbar.md` | 69 | never audited, has steps |
| 93 | `desktop-dash/backend-communication.md` | 93 | never audited, has steps |

### Documentation (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 94 | `documentation/skill-scope.md` | 75 | never audited, has imports |
| 95 | `documentation/when-to-switch-pattern.md` | 75 | never audited, has steps |

### Textual (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 96 | `textual/background-workers.md` | 62 | never audited, has imports |
| 97 | `textual/testing.md` | 115 | 6 code blocks, medium, has imports |

### TUI (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 98 | `tui/data-contract.md` | 238 | 17 path refs, large, has steps, edited |
| 99 | `tui/view-switching.md` | 106 | 6 path refs, medium, has steps |

### Root-Level (2 docs)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 100 | `conventions.md` | 167 | 7 code blocks, medium, has imports |
| 101 | `guide.md` | 127 | 3 code blocks, medium, has steps |

### Capabilities (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 102 | `capabilities/adding-new-capabilities.md` | 131 | 10 path refs, medium, has steps |

### Checklists (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 103 | `checklists/investigation-findings.md` | 247 | large, has steps, line refs |

### Claude-Code (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 104 | `claude-code/skill-composition-patterns.md` | 88 | never audited, has steps |

### Commands (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 105 | `commands/step-renumbering-checklist.md` | 69 | never audited, has steps |

### Config (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 106 | `config/codespaces-toml.md` | 116 | 5 path refs, medium, has steps, line refs, edited |

### Erk-Dev (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 107 | `erk-dev/testing.md` | 54 | never audited, has imports |

### Gateway (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 108 | `gateway/codespace-registry.md` | 75 | 10 path refs, has steps, line refs |

### Integrations (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 109 | `integrations/linear-primitives.md` | 202 | 8 path refs, large, has steps, edited |

### Reference (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 110 | `reference/cli-flag-patterns.md` | 135 | 6 code blocks, medium, has steps |

### Reviews (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 111 | `reviews/development.md` | 157 | 7 path refs, medium, has steps |

### Workflows (1 doc)

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 112 | `workflows/git-sync-state-preservation.md` | 55 | never audited, has steps |

## Implementation Strategy

### Batch Processing Order

Process categories in this order (largest first to front-load the heaviest work, then group related categories):

1. **Architecture** (20 docs) — Largest batch. Many docs reference `src/erk/` source files. Read referenced source files before auditing to build context.
2. **Planning** (20 docs) — Tied for largest. References `.impl/`, `src/erk/cli/commands/exec/`, and planning workflows.
3. **CI** (13 docs) — References `.github/workflows/` and `src/erk/cli/commands/exec/`. Independent from other batches.
4. **CLI** (12 docs) — References `src/erk/cli/` heavily. Process after architecture since some docs cross-reference.
5. **Erk** (5 docs) — General erk workflow docs.
6. **Testing** (5 docs) — References `tests/` patterns.
7. **Sessions** (4 docs) — References session-related source files.
8. **Hooks** (3 docs) — References `.claude/hooks/`.
9. **Objectives** (3 docs) — References `src/erk/objectives/`.
10. **PR Operations** (3 docs) — References PR-related scripts.
11. **Review** (3 docs) — Review workflow docs.
12. **Remaining categories** (21 docs across 13 categories) — Process all smaller batches (desktop-dash, documentation, textual, tui, root, capabilities, checklists, claude-code, commands, config, erk-dev, gateway, integrations, reference, reviews, workflows).

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

### Score-4 Document Characteristics

Score-4 documents are in the LOW priority tier (score 3-5). These typically have fewer red flags than higher-scored documents. Common score-4 patterns include:

- **Never-audited + one signal** (e.g., steps or imports): These often need just a frontmatter stamp and a quick path check. Many will be clean.
- **Previously audited (edited) + multiple signals**: These were already fixed once. The `edited (-1)` deduction means they have 5 points of raw signals minus the deduction. These need careful re-verification since code may have changed since the last audit.
- **Medium-sized with path refs + steps**: Documents that describe multi-step procedures with source code references. Focus verification on path accuracy and procedure correctness.

Given the LOW priority tier, expect a higher proportion of `clean` stamps compared to higher-score batches. Many of these documents may have been previously partially audited or maintained through normal development.

### Discovery Script

To identify the exact documents at implementation time (scores may shift slightly if intervening PRs land), use this discovery command:

```bash
python3 -c "
import re
from pathlib import Path
from datetime import datetime

docs = Path('docs/learned')
today = datetime(2026, 2, 17)

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
    if s == 4:
        print(str(f.relative_to(docs)))
"
```

If the count differs significantly from 112 (e.g., by more than 15), include any docs that score 3 or 5 that were in the original list above, to ensure comprehensive coverage.

## Files NOT Changing

- **Source code files** (`src/`, `tests/`, `.github/`) — This is a documentation-only audit. Source code is read for verification but never modified.
- **Auto-generated files** (`docs/learned/index.md`, `docs/learned/tripwires-index.md`, per-category `index.md`) — These are regenerated by `erk docs sync`.
- **CHANGELOG.md** — Never modify directly.
- **`.claude/` configuration** — Commands, skills, and hooks are not modified.

## Verification

After all documents are audited:

1. **Run `erk docs sync`** to regenerate index files and fix any cross-references broken by edits
2. **Verify no regressions** — Run `python3 -m pytest tests/unit/agent_docs/ -x` via devrun to ensure frontmatter validation passes
3. **Count check** — Verify that all 112 target documents now have `last_audited` fields:
   ```bash
   grep -rl "last_audited" docs/learned/ | wc -l
   ```
   This count should be at least 310 + 112 = 422 (current audited count + this batch). Some docs may have been audited between planning and implementation, so the count could be slightly higher.
4. **Score check** — Re-run the discovery script above. All 112 documents should now score 0-2 (SKIP tier) due to fresh `last_audited` dates.