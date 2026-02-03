# Plan: `/local:audit-doc` Command

## Goal

Create a command that adversarially analyzes a `docs/learned/` document to assess whether it provides meaningful value over the underlying source code. Documents that merely restate what code already communicates should be flagged for simplification or replacement with code references.

## Command File

**Create:** `.claude/commands/local/audit-doc.md`

## Command Design

### Usage

```bash
/local:audit-doc docs/learned/architecture/subprocess-wrappers.md
/local:audit-doc architecture/subprocess-wrappers.md   # relative to docs/learned/
```

### Phases

#### Phase 1: Resolve and Read Document

- Parse `$ARGUMENTS` to resolve the doc path (accept absolute, repo-relative, or docs/learned/-relative paths)
- Read the document fully
- Extract frontmatter (`title`, `read_when`, `tripwires`)

#### Phase 2: Extract Code References

Parse the document to identify all references to source code:
- Explicit file paths (`src/erk/...`, `packages/...`)
- Import statements in code blocks (`from erk.foo import bar`)
- Function/class/variable names mentioned
- Code examples that demonstrate usage

#### Phase 3: Read Referenced Source Code

For each referenced source file:
- Read the actual source code
- Find the referenced functions/classes
- Capture docstrings, type signatures, and inline comments

#### Phase 4: Adversarial Analysis

For each section of the document, classify it into one of these value categories:

| Category | Description | Action |
|----------|-------------|--------|
| **DUPLICATIVE** | Restates what code already says (signatures, imports, basic behavior) | Replace with "Read `path:line`" reference |
| **DRIFT RISK** | Documents specific values, paths, or behaviors that will change | Flag as high-maintenance; consider code reference instead |
| **HIGH VALUE** | Captures *why* decisions were made, trade-offs, decision tables, patterns across files | Keep |
| **CONTEXTUAL** | Connects multiple code locations into a coherent narrative the code alone can't provide | Keep |
| **EXAMPLES** | Code examples that are essentially identical to what exists in source/tests | Replace with reference to actual test/source |

Specific things to flag as duplicative:
- Import paths (agents can find these via grep)
- Function signatures (agents can read the source)
- Basic "what it does" descriptions that match docstrings
- Code examples that duplicate test cases
- File path listings that could be found via glob

Specific things to flag as high-value:
- Decision tables ("when to use X vs Y")
- Anti-patterns / "don't do this" warnings
- Cross-cutting patterns that span multiple files
- Historical context / "why not the obvious approach"
- Tripwires that prevent common mistakes

#### Phase 5: Generate Report

```markdown
## Doc Audit: <doc-title>

### Verdict: KEEP / SIMPLIFY / REPLACE WITH CODE REFS / CONSIDER DELETING

### Value Breakdown

| Section | Lines | Classification | Reasoning |
|---------|-------|---------------|-----------|
| ... | ... | ... | ... |

### Duplicative Content (X% of document)

[List specific sections that restate code, with the source location that makes them redundant]

### High-Value Content (X% of document)

[List sections that provide genuine value over code]

### Drift Risks

[Sections likely to become stale as code evolves]

### Recommended Rewrite

[If SIMPLIFY verdict: suggest a slimmed-down version that keeps high-value content and replaces duplicative content with code references]
```

#### Phase 6: Offer Actions

AskUserQuestion with options:
- "Show me the recommended rewrite"
- "Apply the recommended rewrite"
- "No action, just noting the findings"

#### Phase 7: Execute (if rewrite selected)

Apply the recommended changes to the document.

## Key Design Decisions

1. **Adversarial framing**: The command should be skeptical of documentation value by default. The burden of proof is on the doc to justify its existence vs just reading code.

2. **Percentage-based scoring**: Showing what % of the doc is duplicative gives a quick signal. A doc that's 80% duplicative is a strong candidate for simplification.

3. **Section-level granularity**: Don't just give a doc-level verdict. Show which sections add value and which don't, so the user can surgically edit.

4. **Concrete code references**: When flagging something as duplicative, always cite the specific source file and line that makes it redundant. This makes the audit actionable.

5. **Drift risk as separate axis**: Something can be non-duplicative today but high-risk for drift. Call this out separately.

## Verification

- Run the command against `docs/learned/architecture/subprocess-wrappers.md` (a doc with a mix of high-value decision tables and duplicative import/signature information)
- Verify it correctly identifies the decision tables as high-value and the import paths as duplicative
- Run against a second doc to confirm generality