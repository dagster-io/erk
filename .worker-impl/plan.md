# Audit 6 Score-11 docs/learned/ Documents (Never Audited)

## Context

This is step 1.2 of objective #7132 ("Audit All docs/learned/ Documents"). The objective works through all documents by audit-scan priority score, starting with the highest. Step 1.1 (PR #7134) audited 7 score 11-12 documents. This step audits the next batch: 6 never-audited score-11 documents.

The audit-scan scoring rubric (defined in `.claude/commands/local/audit-scan.md`) assigns points based on: missing audit metadata (+3), large line count (+1/+2), code blocks (+2), file path references (+2), broken paths (+3), imports (+1), step sequences (+1), behavioral claim density (+2), line number references (+1), with deductions for redirects (-2) and recently-edited status (-1).

All 6 target documents have **never been audited** (no `last_audited` field), which contributes +3 to their score. They are the largest never-audited documents scoring 11.

## Documents to Audit

| # | Document | Lines | Key Signals |
|---|----------|-------|-------------|
| 1 | `claude-code/context-fork-feature.md` | 189 | No audit (+3), code blocks, source comments referencing `.claude/commands/` and `.claude/skills/` |
| 2 | `cli/exec-command-patterns.md` | 182 | No audit (+3), code blocks, refs to `src/erk/cli/commands/exec/scripts/` |
| 3 | `ci/claude-code-docker.md` | 161 | No audit (+3), code blocks, CI-specific Docker patterns |
| 4 | `reviews/development.md` | 154 | No audit (+3), code blocks, refs to `src/erk/review/` modules |
| 5 | `cli/checkout-helpers.md` | 147 | No audit (+3), refs to `src/erk/cli/commands/checkout_helpers.py` |
| 6 | `ci/github-actions-label-filtering.md` | 146 | No audit (+3), code blocks, refs to `src/erk/cli/constants.py` |

## Changes

### For Each Document: Apply `/local:audit-doc` Methodology

For each of the 6 documents, perform the full audit process defined in `.claude/commands/local/audit-doc.md`:

**Prerequisites:**
- Load the `learned-docs` skill FIRST (read `.claude/skills/learned-docs/learned-docs-core.md`)
- Read `docs/learned/documentation/audit-methodology.md` for classification guidance

**Per-document process:**

1. **Read the document** fully and extract frontmatter
2. **Extract code references** — identify all `src/`, `packages/`, `tests/`, `.claude/` paths and symbols
3. **Read referenced source code** — verify functions/classes exist, capture collateral findings
4. **Verify system descriptions** — confirm workflows, behaviors, imports, symbols, types match reality
5. **Adversarial analysis** — classify each section as DUPLICATIVE, INACCURATE, DRIFT RISK, HIGH VALUE, CONTEXTUAL, REFERENCE CACHE, or EXAMPLES
6. **Code block triage** — classify each code block as ANTI-PATTERN, CONCEPTUAL, VERBATIM, REFERENCE TABLE, or TEMPLATE
7. **Generate verdict** — produce brief summary with percentages and planned changes
8. **Apply changes** — use `--auto-apply` behavior since this is CI: KEEP→stamp clean, NEEDS_UPDATE→fix+stamp, SIMPLIFY→rewrite+stamp, CONSIDER DELETING→stamp only
9. **Apply collateral fixes** — fix mechanical issues (stale comments, broken links) in other files; recommend separate audits for conceptual issues

### Document-Specific Pre-Audit Notes

#### 1. `claude-code/context-fork-feature.md` (189 lines)
- Documents the `context: fork` frontmatter feature for skills/commands
- Contains `<!-- Source: ... -->` comments referencing `.claude/commands/local/audit-doc.md`, `.claude/commands/local/audit-scan.md`, `.claude/commands/erk/learn.md`, and `.claude/skills/pr-feedback-classifier/SKILL.md` — all verified to exist
- This is primarily CONTEXTUAL/HIGH VALUE content — explains design decisions around context isolation that aren't evident from code alone
- No tripwires field — might be missing or intentionally absent; check frontmatter schema
- Verify the `context: fork` feature description matches current Claude Code behavior (this is third-party documentation about Claude Code features, classify as REFERENCE CACHE where appropriate)

#### 2. `cli/exec-command-patterns.md` (182 lines)
- Documents patterns for writing `erk exec` scripts with PR/issue output
- References `src/erk/cli/commands/exec/scripts/handle_no_changes.py` (EXISTS) and `src/erk/cli/commands/exec/scripts/validate_plan_content.py` (EXISTS)
- Verify the `_build_pr_body()` and `_build_issue_comment()` patterns described still match the actual implementations in those files
- Check if code examples are VERBATIM copies of source or CONCEPTUAL illustrations

#### 3. `ci/claude-code-docker.md` (161 lines)
- Documents container-based approach for running Claude Code in GitHub Actions
- References `containerless-ci.md` — verify this cross-reference still exists
- Contains Docker-specific patterns (root user workarounds, temp directory permissions)
- Likely a mix of REFERENCE CACHE (Docker/CI knowledge) and CONTEXTUAL (erk-specific patterns)
- Check if the erk project still uses Docker-based CI or has migrated to containerless

#### 4. `reviews/development.md` (154 lines)
- Documents the convention-based review system creation process
- References `src/erk/review/parsing.py` (EXISTS), `src/erk/review/prompt_assembly.py` (EXISTS), `src/erk/cli/commands/exec/scripts/run_review.py` (EXISTS)
- Contains `<!-- Source: ... -->` comments with specific function references — verify `discover_matching_reviews`, `validate_review_frontmatter`, `REVIEW_PROMPT_TEMPLATE`, `run_review` still exist in those locations
- Cross-references `docs/learned/ci/review-spec-format.md` — verify exists
- This is likely HIGH VALUE: explains the review system architecture that spans multiple files

#### 5. `cli/checkout-helpers.md` (147 lines)
- Documents the `src/erk/cli/commands/checkout_helpers.py` module (EXISTS)
- Also references `src/erk/cli/commands/navigation_helpers.py` (EXISTS) in a tripwire about import cycles
- Verify `ensure_branch_has_worktree()` and `navigate_and_display_checkout()` functions still exist with the described signatures
- Check if the three checkout command variants mentioned still exist and use these helpers

#### 6. `ci/github-actions-label-filtering.md` (146 lines)
- Documents label-based CI gating patterns in GitHub Actions
- References `src/erk/cli/constants.py` (EXISTS) for `PLAN_REVIEW_LABEL`
- Contains `<!-- Source: ... -->` comment for the constant reference
- Verify `PLAN_REVIEW_LABEL` still exists in `constants.py`
- Likely a mix of REFERENCE CACHE (GitHub Actions label syntax) and CONTEXTUAL (erk-specific label patterns)
- Frontmatter is slightly unusual: `read_when` uses bare strings without quotes, and `tripwires` use `action:` without wrapping in quotes on some entries — verify this passes frontmatter validation

### Frontmatter Updates

For every document audited, add these frontmatter fields (none of these docs currently have them):

```yaml
last_audited: "YYYY-MM-DD HH:MM PT"  # Current time in 24h Pacific format
audit_result: clean | edited          # clean if no changes; edited if rewritten
```

### Post-Audit: Run `erk docs sync`

After all 6 documents have been audited and any edits applied, run `erk docs sync` to regenerate auto-generated index and tripwire files. This ensures any tripwire changes propagate correctly.

## Implementation Details

### Execution Strategy

Run audits sequentially (not in parallel) because:
- Each audit reads source files that may overlap with other audits
- Collateral fixes from one audit may affect files referenced by another
- Sequential execution ensures consistent state

### Skill Loading

Load `learned-docs` skill once at the start. It persists for the session and provides the content quality standards used throughout.

### Code Patterns to Follow

- **LBYL**: Check paths exist before claiming they're broken
- **Source pointers**: When replacing VERBATIM code blocks, use the format from `.claude/skills/learned-docs/learned-docs-core.md`
- **One Code Rule exceptions**: ANTI-PATTERN, CONCEPTUAL, INPUT/OUTPUT EXAMPLES, and REFERENCE TABLES are legitimate keeps
- **Constants exception**: Constants and defaults mentioned in prose are HIGH VALUE, not duplicative

### Audit Result Format

For each document, output the standard verdict line:
```
Audit: <doc-path> | Verdict: <VERDICT> | Duplicative: X% | Inaccurate: X% | High-value: Y%
Verification: X verified | Y broken/stale
```

### Commit Message Format

After all audits are complete, commit with a message like:
```
Audit 6 never-audited score-11 docs/learned/ documents
```

The commit should list which documents were audited and their verdicts in the body.

## Files NOT Changing

- **Source code files** — only documentation in `docs/learned/` is being modified, unless collateral findings require fixing stale comments in source files already referenced by the audited docs
- **Auto-generated files** — `index.md`, `tripwires.md` files will be regenerated by `erk docs sync` but should not be manually edited
- **CHANGELOG.md** — never modified directly
- **Test files** — no test changes needed for documentation audits

## Verification

1. **All 6 docs have `last_audited` and `audit_result`** in frontmatter with today's date
2. **No broken file path references** remain in the 6 audited docs (broken paths either fixed or removed)
3. **`erk docs sync` succeeds** without errors after all edits
4. **CI passes**: Run `make check` to verify formatting and linting pass
5. **Verdict summary**: Each document has a recorded verdict (KEEP, SIMPLIFY, NEEDS_UPDATE, or CONSIDER DELETING) with percentage breakdowns