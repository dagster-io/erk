---
name: Doc Audit Review
paths:
  - "docs/learned/**/*.md"
marker: "<!-- doc-audit-review -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Get PR Diff and Identify Changed Doc Files

Run `gh pr diff` and filter to `docs/learned/**/*.md` files in the PR.

For each changed doc file, read the full file content using the Read tool.

## Step 2: Load Audit Methodology

Read `.claude/commands/local/audit-doc.md` to understand the audit methodology and classification logic.

This command defines six value categories:

| Category        | Description                                                                                                                                  | Action                                                    |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **DUPLICATIVE** | Restates what code already says (signatures, imports, basic behavior)                                                                        | Replace with "Read `path:line`" reference                 |
| **DRIFT RISK**  | Documents specific values, paths, or behaviors that will change                                                                              | Flag as high-maintenance; consider code reference instead |
| **HIGH VALUE**  | Captures _why_ decisions were made, trade-offs, decision tables, patterns across files                                                       | Keep                                                      |
| **CONTEXTUAL**  | Connects multiple code locations into a coherent narrative the code alone can't provide                                                      | Keep                                                      |
| **EXAMPLES**    | Code examples that are essentially identical to what exists in source/tests                                                                  | Replace with reference to actual test/source              |
| **CONTRADICTS** | States something that is factually wrong per the current codebase (wrong function names, incorrect behavior descriptions, outdated patterns) | Flag as high-priority fix; correct or delete              |

## Step 3: For Each Changed Doc, Apply Audit-Doc Phases 2-4

For each doc file changed in the PR, apply these phases from the audit-doc methodology:

### Phase 2: Extract Code References

Parse the document to identify all references to source code:

- Explicit file paths (`src/erk/...`, `packages/...`)
- Import statements in code blocks (`from erk.foo import bar`)
- Function/class/variable names mentioned
- Code examples that demonstrate usage

Create a list of all referenced source files and symbols.

### Phase 3: Read Referenced Source Code

For each referenced source file:

- Read the actual source code
- Find the referenced functions/classes
- Capture docstrings, type signatures, and inline comments

### Phase 4: Adversarial Section-by-Section Classification

For each section of the document **that appears on `+` lines in the diff** (new or modified content), classify it:

- **DUPLICATIVE**: Restates what code already says (signatures, imports, basic behavior)
- **DRIFT RISK**: Documents specific values, paths, or behaviors that will change
- **HIGH VALUE**: Captures _why_ decisions were made, trade-offs, decision tables, patterns across files
- **CONTEXTUAL**: Connects multiple code locations into a coherent narrative
- **EXAMPLES**: Code examples that duplicate what exists in source/tests
- **CONTRADICTS**: States something that is factually wrong per the current codebase (wrong function names, incorrect behavior descriptions, outdated patterns)

**Only analyze sections on `+` lines in the diff.** Do not flag pre-existing content.

**Specific things to flag as contradictory:**

- Prose describing behavior that doesn't match actual code behavior
- Function/class names that don't exist or have been renamed
- Described parameters, return types, or signatures that don't match source
- Workflow descriptions that reference removed or restructured code paths
- Pattern guidance that contradicts what the codebase actually does

**Specific things to flag as duplicative:**

- Import paths (agents can find these via grep)
- Function signatures (agents can read the source)
- Basic "what it does" descriptions that match docstrings
- Code examples that duplicate test cases
- File path listings that could be found via glob

**Specific things to flag as high-value:**

- Decision tables ("when to use X vs Y")
- Anti-patterns / "don't do this" warnings
- Cross-cutting patterns that span multiple files
- Historical context / "why not the obvious approach"
- Tripwires that prevent common mistakes

## Step 4: Post Inline Comments for Problematic Sections

For each section classified as **DUPLICATIVE**, **DRIFT RISK**, or **CONTRADICTS**, post an inline comment at the start of the section:

```
**Doc Audit**: [DUPLICATIVE] — This section restates [what the code already communicates].

Source: `<source_file_path>:<line>`

Suggested fix: Replace with code reference:
> See `SymbolName` in `<relative_path>:<line>`.
```

Example inline comment:

```
**Doc Audit**: [DUPLICATIVE] — This section restates function signatures and import paths that agents can find via grep.

Source: `src/erk/gateway/git/git.py:45`

Suggested fix: Replace with code reference:
> See `Git.add()` in `src/erk/gateway/git/git.py:45`.
```

For **DRIFT RISK** sections:

```
**Doc Audit**: [DRIFT RISK] — This section documents specific values/paths that will change.

Source: `<source_file_path>:<line>`

Risk: High maintenance burden as code evolves. Consider replacing with code reference or removing if the code is self-documenting.
```

For **CONTRADICTS** sections:

```
**Doc Audit**: [CONTRADICTS] — This section states [X] but the code actually does [Y].

Source: `<source_file_path>:<line>`

Suggested fix: Correct the prose to match actual behavior, or remove the section.
```

## Step 5: Post Summary Comment

Post a summary comment with this format (preserve existing Activity Log entries and prepend new entry):

```
### Doc Audit Review

| File | Verdict | Duplicative % | High Value % | Comments |
|------|---------|---------------|-------------|----------|
| `docs/learned/foo.md` | SIMPLIFY | 60% | 30% | 3 |
| `docs/learned/bar.md` | KEEP | 10% | 70% | 0 |

(Only list files that were checked.)

**Verdicts:**
- **KEEP**: High-value content dominates (≥50% HIGH VALUE or CONTEXTUAL)
- **SIMPLIFY**: Significant duplicative or contradictory content (≥30% DUPLICATIVE, CONTRADICTS, or DRIFT RISK) but has high-value sections worth preserving
- **REPLACE WITH CODE REFS**: Mostly duplicative (≥60% DUPLICATIVE, CONTRADICTS, or DRIFT RISK), minimal high-value content
- **CONSIDER DELETING**: Almost entirely duplicative (≥80% DUPLICATIVE, CONTRADICTS, or DRIFT RISK), no meaningful high-value content

CONTRADICTS is treated as at least as severe as DUPLICATIVE — contradictory docs are actively misleading.

### Activity Log
- [timestamp] Audited 2 docs: 1 SIMPLIFY, 1 KEEP (3 DUPLICATIVE sections flagged)
- [timestamp] All docs clean, no duplicative content detected
- [timestamp] Audited 1 doc: REPLACE WITH CODE REFS (5 DUPLICATIVE sections flagged)

(Keep last 10 entries maximum. Prepend new entry at the top.)
```

Activity log entry examples:

- "Audited 2 docs: 1 SIMPLIFY, 1 KEEP (3 DUPLICATIVE sections flagged)"
- "All docs clean, no duplicative content detected"
- "Audited 1 doc: REPLACE WITH CODE REFS (5 DUPLICATIVE sections flagged)"
- "No changes to docs/learned/ in this PR"

Keep the last 10 log entries maximum.

## Key Design Notes

1. **Only audit `+` lines**: Don't flag pre-existing content in unchanged sections. Only flag new/modified content being added in the PR.

2. **The audit-doc command is the source of truth**: Reference `.claude/commands/local/audit-doc.md` for the classification logic. The review is a thin wrapper that adapts the output format to inline PR comments and a summary table.

3. **Percentage-based scoring**: Show what % of the doc is duplicative/high-value for quick signal. A doc that's 80% duplicative is a strong candidate for simplification.

4. **Concrete code references**: When flagging something as duplicative, always cite the specific source file and line that makes it redundant. This makes the review actionable.

5. **Verdicts based on percentages** (CONTRADICTS counts the same as DUPLICATIVE in all thresholds):
   - KEEP: ≥50% high-value content
   - SIMPLIFY: ≥30% duplicative/contradictory but has high-value sections
   - REPLACE WITH CODE REFS: ≥60% duplicative/contradictory, minimal high-value content
   - CONSIDER DELETING: ≥80% duplicative/contradictory, no meaningful high-value content

6. **Complements learned-docs review**: The learned-docs review checks for verbatim source code copies in code blocks. This review checks for duplicative documentation sections that restate what code communicates. Different concerns, no overlap.
