---
name: Audit PR Docs
paths:
  - "docs/learned/**/*.md"
marker: "<!-- audit-pr-docs -->"
model: claude-opus-4-6
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Load Standards and Analysis Methodology

Read these files from the repository:

1. `.claude/skills/learned-docs/learned-docs-core.md` — content rules, the One Code Rule, four exceptions
2. `docs/learned/documentation/source-pointers.md` — replacement format, 5-line threshold, decision checklist
3. `.claude/commands/local/audit-doc.md` — analysis methodology (Extract Code References through Code Block Triage) and verdict thresholds (Generate Report phase)

These define what counts as a verbatim copy, what exceptions exist, the replacement format, and the full analysis methodology. The audit-doc command is the single source of truth for how to analyze a learned doc — this review file only defines the review mechanics (diff filtering, PR comment format, summary format).

## Step 2: Identify Changed Doc Files

Run `gh pr diff` and extract file paths matching `docs/learned/**/*.md`.

For each changed doc file, read the **full file content** using the Read tool (not just the `+` lines from the diff). When a doc is touched in a PR, audit the entire document to surface pre-existing issues alongside new ones.

## Step 3: Audit Each Changed Doc

For each doc file identified in Step 2, apply audit-doc's analysis phases:

- **Extract Code References**: file paths, imports, function/class names
- **Read Referenced Source Code**: actual source, docstrings, type signatures
- **Verify System Descriptions**: confirm descriptions match reality
- **Adversarial Analysis**: classify each section as DUPLICATIVE, INACCURATE, DRIFT RISK, HIGH VALUE, CONTEXTUAL, REFERENCE CACHE, or EXAMPLES
- **Code Block Triage**: classify each code block as VERBATIM, ANTI-PATTERN, CONCEPTUAL, or TEMPLATE

Then compute the verdict using audit-doc's Generate Report thresholds (KEEP, SIMPLIFY, REPLACE WITH CODE REFS, CONSIDER DELETING).

These classifications produce PR comments:

- **VERBATIM** code blocks → inline comment (Step 4)
- **INACCURATE** claims → inline comment (Step 4)
- **DUPLICATIVE** sections → inline comment (Step 4)
- **DRIFT RISK** sections → inline comment (Step 4)

All other classifications (ANTI-PATTERN, CONCEPTUAL, TEMPLATE, REFERENCE TABLE, HIGH VALUE, CONTEXTUAL, REFERENCE CACHE, EXAMPLES) are noted in the summary but do not produce inline PR comments.

## Step 4: Post Inline Comments

### Verbatim Code Blocks

For each VERBATIM code block found in Step 3, post an inline comment at the start of the code block:

```
**Audit PR Docs**: Verbatim source code copy detected.

Source: `<source_file_path>:<start_line>-<end_line>`

This code block copies ~N lines from the source file and will go stale if the source changes.

Suggested fix: Replace with the source pointer format from `docs/learned/documentation/source-pointers.md` (HTML comment + prose reference).
```

### Inaccurate Claims

For each INACCURATE claim found in Step 3, post an inline comment at the relevant line:

```
**Audit PR Docs**: Inaccurate claim detected.

Claim: "<what the doc says>"
Reality: "<what the code actually does>"

Source: `<source_file_path>:<line>`

Suggested fix: <specific correction>
```

### Duplicative Sections

For each DUPLICATIVE section found in Step 3, post an inline comment at the start of the section:

```
**Audit PR Docs**: Duplicative section — restates what code already communicates.

Source: `<source_file_path>:<line>`

Suggested fix: Replace with code reference:
> See `SymbolName` in `<relative_path>`.
```

### Drift Risk Sections

For each DRIFT RISK section found in Step 3, post an inline comment at the start of the section:

```
**Audit PR Docs**: Drift risk — documents specific values/paths that will change.

Source: `<source_file_path>:<line>`

Risk: High maintenance burden as code evolves. Consider replacing with code reference or removing if the code is self-documenting.
```

## Step 5: Summary Comment

Post a summary comment with this format (preserve existing Activity Log entries and prepend new entry):

```
### Audit PR Docs

| File | Verdict | Duplicative % | High Value % | Issues |
|------|---------|---------------|-------------|--------|
| `docs/learned/foo/bar.md` | SIMPLIFY | 40% | 30% | 2 verbatim, 1 inaccurate |
| `docs/learned/baz/qux.md` | KEEP | 5% | 70% | 0 |

(Only list files that were checked.)

### Activity Log
- [timestamp] Audited 2 docs: 1 SIMPLIFY, 1 KEEP (2 verbatim blocks, 1 inaccurate claim)
- [timestamp] All docs clean, no issues detected

(Keep last 10 entries maximum. Prepend new entry at the top.)
```

## Key Design Notes

1. **Full doc audit on touch**: When a doc is modified in a PR, audit the entire document — not just added lines. This surfaces pre-existing issues when a doc is being actively worked on.
2. **Analysis delegated to audit-doc**: This file defines only review mechanics (diff filtering, PR comment format, summary format). All analysis methodology and verdict thresholds live in `audit-doc.md`.
3. **Actionable comments with source paths**: Each comment includes the exact source path so a reviewer agent or human can immediately fix it without investigation.
