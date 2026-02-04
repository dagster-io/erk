---
description: Audit a learned doc for value vs code duplication
---

# /local:audit-doc

Adversarially analyze a `docs/learned/` document to assess whether it provides meaningful value over the underlying source code.

## Goal

Identify documentation that merely restates what code already communicates. Flag duplicative content for simplification or replacement with code references.

## Usage

```bash
/local:audit-doc docs/learned/architecture/subprocess-wrappers.md
/local:audit-doc architecture/subprocess-wrappers.md   # relative to docs/learned/
/local:audit-doc architecture/subprocess-wrappers.md --auto-apply   # skip prompts, auto-apply verdict actions
```

## Instructions

### Phase 1: Resolve and Read Document

Parse `$ARGUMENTS` to:

1. Detect if `--auto-apply` flag is present (strip from path arguments)
2. **CI auto-detection:** If `--auto-apply` was not explicitly passed, check for CI environment:
   - Run: `[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"`
   - If CI detected, automatically enable `--auto-apply` mode and output: "CI environment detected: enabling --auto-apply mode"
3. Resolve the doc path:
   - If starts with `docs/learned/`: Use as-is
   - If starts with `/`: Use as absolute path
   - Otherwise: Treat as relative to `docs/learned/`

Store whether `--auto-apply` mode is active for use in Phase 6.

Read the document fully and extract frontmatter (`title`, `read_when`, `tripwires`).

If the frontmatter contains `last_audited` and `audit_result`, display them at the start of the report:

```
Last audited: YYYY-MM-DD HH:MM PT (result: clean/edited)
```

If no audit metadata is present, note: "No previous audit recorded."

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

### Phase 4: Adversarial Analysis

For each section of the document, classify it into one of these value categories:

| Category        | Description                                                                                                                                  | Action                                                    |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **DUPLICATIVE** | Restates what code already says (signatures, imports, basic behavior)                                                                        | Replace with "Read `path:line`" reference                 |
| **DRIFT RISK**  | Documents specific values, paths, or behaviors that will change                                                                              | Flag as high-maintenance; consider code reference instead |
| **HIGH VALUE**  | Captures _why_ decisions were made, trade-offs, decision tables, patterns across files                                                       | Keep                                                      |
| **CONTEXTUAL**  | Connects multiple code locations into a coherent narrative the code alone can't provide                                                      | Keep                                                      |
| **EXAMPLES**    | Code examples that are essentially identical to what exists in source/tests                                                                  | Replace with reference to actual test/source              |
| **CONTRADICTS** | States something that is factually wrong per the current codebase (wrong function names, incorrect behavior descriptions, outdated patterns) | Flag as high-priority fix; correct or delete              |

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
- **Exception**: Constants, default values, and configuration strings mentioned in prose context are NOT duplicative — they make docs scannable and should be classified as HIGH VALUE or CONTEXTUAL

**Specific things to flag as high-value:**

- Decision tables ("when to use X vs Y")
- Anti-patterns / "don't do this" warnings
- Cross-cutting patterns that span multiple files
- Historical context / "why not the obvious approach"
- Tripwires that prevent common mistakes
- Constants and default values mentioned in prose context (e.g., "defaults to `premiumLinux`") — these make docs scannable without requiring a code read

### Phase 5: Generate Report

Complete the full internal analysis from Phase 4, but output only a brief summary regardless of mode. Never output the full value breakdown table, duplicative content detail sections, or recommended rewrite text.

**Output format (always):**

```
Audit: <doc-path> | Verdict: <VERDICT> | Duplicative: X% | High-value: Y% | Contradictions: <count>
```

Follow with 2-3 sentences describing the planned changes. For example:

> Sections "Import Paths" and "Function Signatures" are duplicative of `src/erk/gateway/git.py:42` and should be replaced with code references. The "Anti-patterns" section contradicts the current implementation of `resolve_path()` which now uses pathlib.

Keep the full internal analysis available for Phase 7 actions — just don't dump it as text output.

### Phase 6: Determine Action

**If `--auto-apply` mode is active:**

Automatically select the action based on the verdict without prompting:

- **KEEP** verdict → Proceed to Phase 7 with "Mark as audited (clean)"
- **SIMPLIFY / REPLACE WITH CODE REFS** verdict → Proceed to Phase 7 with "Mark as audited (with rewrite)" (apply rewrite + stamp)
- **CONSIDER DELETING** verdict → Proceed to Phase 7 with "Mark as audited (clean)" (stamp only, don't auto-delete)

**If `--auto-apply` mode is NOT active:**

Use AskUserQuestion to offer:

- **"Apply recommended rewrite"** — rewrite the doc to remove duplicative content (only offer if verdict is SIMPLIFY or REPLACE WITH CODE REFS)
- **"Mark as audited (clean)"** — stamp frontmatter with audit date and `clean` result (use when verdict is KEEP)
- **"Mark as audited (with rewrite)"** — apply the rewrite AND stamp frontmatter (only offer if verdict is SIMPLIFY or REPLACE WITH CODE REFS)
- **"No action"** — just noting findings

### Phase 7: Execute Actions

Based on the user's choice:

**If rewrite selected** (either "Apply recommended rewrite" or "Mark as audited (with rewrite)"):
Use the Edit tool to apply the recommended rewrite to the document.

**If audit stamp selected** (either "Mark as audited (clean)" or "Mark as audited (with rewrite)"):
Update the document's YAML frontmatter to add or update audit metadata:

```yaml
last_audited: "YYYY-MM-DD HH:MM PT"
audit_result: clean | edited
```

- Use `clean` when the audit found no significant issues (KEEP verdict, no rewrite applied)
- Use `edited` when the doc was rewritten to remove duplicative content

If the document already has `last_audited` / `audit_result` fields, overwrite them with the new values. Use the current date and time in Pacific time, down to the minute.

## Design Principles

1. **Adversarial framing**: Be skeptical of documentation value by default. The burden of proof is on the doc to justify its existence vs just reading code.

2. **Percentage-based scoring**: Show what % of the doc is duplicative or contradictory for quick signal. A doc that's 80% duplicative is a strong candidate for simplification. Any contradictory content is treated as at least as severe as duplicative content in verdict calculations.

3. **Section-level granularity**: Don't just give a doc-level verdict. Show which sections add value and which don't, so the user can surgically edit.

4. **Concrete code references**: When flagging something as duplicative, always cite the specific source file and line that makes it redundant. This makes the audit actionable.

5. **Drift risk as separate axis**: Something can be non-duplicative today but high-risk for drift. Call this out separately.
