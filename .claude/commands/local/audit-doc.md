---
description: Audit a learned doc for accuracy and value vs code
context: fork
agent: general-purpose
---

# /local:audit-doc

Adversarially analyze a `docs/learned/` document to assess whether it provides meaningful value over the underlying source code.

## Goal

Identify documentation that: (1) describes systems, workflows, or concepts inaccurately, or (2) merely restates what code already communicates. Flag inaccurate content for correction and duplicative content for simplification or replacement with code references.

## Usage

```bash
/local:audit-doc docs/learned/architecture/subprocess-wrappers.md
/local:audit-doc architecture/subprocess-wrappers.md   # relative to docs/learned/
/local:audit-doc architecture/subprocess-wrappers.md --auto-apply   # skip prompts, auto-apply verdict actions
```

## Instructions

### Prerequisites

**MANDATORY:** Load the `learned-docs` skill before starting any phase. This skill defines the content quality standards that drive all classification decisions in this audit. Without it, the audit will miss standards violations (source pointer format, One Code Rule, explain-why-not-what, enumerable catalogs).

### Phase 1: Resolve and Read Document

**FIRST:** Read `.claude/skills/learned-docs/learned-docs-core.md` using the Read tool. All subsequent phases depend on these rules — specifically:

- The One Code Rule and its four exceptions (Phase 6: Code Block Triage)
- Source pointer format: name-based over line-range (Phase 2, Phase 5)
- "Explain why, not what" (Phase 5: Adversarial Analysis)
- "Enumerable catalogs → source pointers, not tables" (Phase 5)
- DUPLICATIVE vs HIGH VALUE classification criteria (Phase 5)

Then proceed to parse `$ARGUMENTS` to:

1. Detect if `--auto-apply` flag is present (strip from path arguments)
2. **CI auto-detection:** If `--auto-apply` was not explicitly passed, check for CI environment:
   - Run: `[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"`
   - If CI detected, automatically enable `--auto-apply` mode and output: "CI environment detected: enabling --auto-apply mode"
3. Resolve the doc path:
   - If starts with `docs/learned/`: Use as-is
   - If starts with `/`: Use as absolute path
   - Otherwise: Treat as relative to `docs/learned/`

Store whether `--auto-apply` mode is active for use in the Determine Action phase.

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

**Collateral finding collection:** While reading source files, watch for stale comments and docstrings in the code you're already examining. If a comment says "returns list" but the function returns a dict, or a docstring documents a parameter that no longer exists, record a structured collateral finding. Scope limit: only record issues visible in code you're already reading for the primary audit — don't hunt through entire files.

Collateral finding format: `{category, file, location, claim, reality, suggested_fix}` where category is one of: `STALE_COMMENT` (SC), `STALE_DOCSTRING` (SD), `BROKEN_CROSS_REF` (BX), `CONTRADICTING_DOC` (CD), `OBSOLETE_SYSTEM` (OS), `CONCEPTUAL_DRIFT` (CF), `STALE_FLOW` (SF).

### Phase 4: Verify System Descriptions

**Primary task:** For each section that describes how a system, workflow, or component works, verify the description matches reality.

**System behavior verification:**

- When doc says "X does Y", trace through the actual code to confirm
- When doc describes a workflow sequence, verify the code follows that sequence
- When doc explains why a pattern is used, check the pattern is actually present

**Concept accuracy verification:**

- When doc defines a term (e.g., "a gateway is..."), verify usage in codebase matches
- When doc describes component responsibilities, verify the component actually does those things

**Concrete claim verification (supporting checks):**

**Import claims**: For each `from X import Y` or `import X` in code blocks:

- Attempt verification by checking if the module path exists in the codebase
- Mark as VERIFIED, BROKEN, or CANNOT_VERIFY

**Symbol claims**: For each function/class name mentioned in prose:

- Search source code for definition (`def name` or `class name`)
- Mark as VERIFIED (found), MISSING (not found), or AMBIGUOUS (multiple matches)

**Type claims**: For each "returns X" or "raises X" claim:

- Find the referenced function's signature/implementation
- Check if return type or exception type matches
- Mark as VERIFIED, MISMATCH, or CANNOT_VERIFY

Record verification results for use in the Adversarial Analysis and Generate Report phases.

**Cross-reference collateral findings:** When following links to other `docs/learned/` files during verification, watch for issues in those referenced documents:

**Conceptual issues (highest priority):** Check whether the referenced doc's _premise_ is still valid:

- Does it describe a system, workflow, or component that still exists? If the system was replaced or removed → record as `OBSOLETE_SYSTEM` (OS)
- Does it use terms/concepts whose meaning has changed in the codebase? → record as `CONCEPTUAL_DRIFT` (CF)
- Does it describe a multi-step flow (numbered steps, flowcharts, sequence descriptions) where the actual steps in code have changed? → record as `STALE_FLOW` (SF)

These checks leverage the code understanding already built in the Read Referenced Source Code phase. If the primary doc references "the plan sync workflow" and the cross-referenced doc describes a 5-step workflow but the code now has 3 steps, that's a `STALE_FLOW`.

**Mechanical issues:** Broken cross-references (`BX`) — links that point to renamed/deleted files. Contradicting specific claims (`CD`) — cross-referenced doc states facts that conflict with code.

**Scope limit:** Don't recursively audit referenced docs. If a referenced doc has systemic problems (e.g., describes an entirely obsolete system), note one `OBSOLETE_SYSTEM` finding recommending a separate audit rather than listing every wrong detail.

### Phase 5: Adversarial Analysis

For each section of the document, classify it into one of these value categories:

| Category            | Description                                                                                                     | Action                                                          |
| ------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **DUPLICATIVE**     | Restates what code already says (signatures, imports, basic behavior)                                           | Replace with "Read `path`" reference                            |
| **INACCURATE**      | States something that doesn't match current code (wrong names, broken imports, incorrect behavior, moved files) | Fix to match reality; correct or replace with code reference    |
| **DRIFT RISK**      | Documents specific values, paths, symbol names (especially private `_method()`), or behaviors that will change  | Flag as high-maintenance; consider code reference instead       |
| **HIGH VALUE**      | Captures _why_ decisions were made, trade-offs, decision tables, patterns across files                          | Keep                                                            |
| **CONTEXTUAL**      | Connects multiple code locations into a coherent narrative the code alone can't provide                         | Keep                                                            |
| **REFERENCE CACHE** | Distilled third-party reference material OR discovered/undocumented API quirks (with `## Sources` section)      | Keep — expensive or impossible to re-acquire                    |
| **EXAMPLES**        | Code examples that are essentially identical to what exists in source/tests                                     | Remove code block; replace with reference to actual test/source |

**Reference cache awareness:** Third-party reference tables and discovered API quirks are NOT duplicative just because the information exists in external documentation. The value is the cached distillation itself. Undocumented quirks discovered through usage are especially high-value — they are literally undiscoverable from official sources.

Apply the content quality standards from the `learned-docs` skill's core rules doc to classify each section. Specifically:

- **Code blocks**: High-drift-risk by default. Apply the skill's "One Code Rule" and four exceptions to determine keep/remove.
- **Duplicative vs high-value**: Apply the skill's "What Belongs vs What Doesn't" criteria. Exception: constants and default values in prose context are NOT duplicative — they make docs scannable.
- **High-value signals**: Decision tables, anti-patterns, cross-cutting patterns, historical context, and tripwires (per the skill's content rules).

### Phase 6: Code Block Triage

For every fenced code block in the document, classify it:

| Classification      | Keep?      | Criteria                                                                |
| ------------------- | ---------- | ----------------------------------------------------------------------- |
| **ANTI-PATTERN**    | Yes        | Shows what NOT to do (wrong way vs right way)                           |
| **CONCEPTUAL**      | Yes        | Illustrates a concept that doesn't exist as a single function in source |
| **VERBATIM**        | **Remove** | Reproduces actual source code (implementation, signatures, usage)       |
| **REFERENCE TABLE** | Yes        | Third-party API tables/syntax that are expensive to re-acquire          |
| **TEMPLATE**        | Maybe      | Shows a pattern for new code — keep only if the pattern isn't in source |

For VERBATIM blocks, apply the replacement format from the `learned-docs` skill's core rules: replace with a prose reference capturing the insight, plus a source pointer. Any doc with unreplaced VERBATIM blocks should receive at minimum a `SIMPLIFY` verdict.

### Phase 7: Generate Report

Complete the full internal analysis from the Adversarial Analysis phase, but output only a brief summary regardless of mode. Never output the full value breakdown table, duplicative content detail sections, or recommended rewrite text.

**Verdict thresholds** (based on section classification percentages):

- **KEEP**: ≥50% HIGH VALUE, CONTEXTUAL, or REFERENCE CACHE
- **SIMPLIFY**: ≥30% DUPLICATIVE/INACCURATE/DRIFT RISK but has high-value sections worth preserving
- **REPLACE WITH CODE REFS**: ≥60% DUPLICATIVE/INACCURATE/DRIFT RISK, minimal high-value content
- **CONSIDER DELETING**: ≥80% DUPLICATIVE/INACCURATE/DRIFT RISK, no meaningful high-value content

INACCURATE is treated as at least as severe as DUPLICATIVE in all threshold calculations.

**Output format (always):**

```
Audit: <doc-path> | Verdict: <VERDICT> | Duplicative: X% | Inaccurate: X% | High-value: Y%
```

Add a verification summary line:

```
Verification: X verified | Y broken/stale
```

Follow with 2-3 sentences describing the planned changes. For example:

> Sections "Import Paths" and "Function Signatures" are duplicative of `src/erk/gateway/git.py` and should be replaced with code references. The "Anti-patterns" section contradicts the current implementation of `resolve_path()` which now uses pathlib.

Keep the full internal analysis available for the Execute Actions phase — just don't dump it as text output.

**Collateral findings report:** If any collateral findings were recorded in the Read Referenced Source Code or Verify System Descriptions phases, append them after the primary audit summary. Conceptual findings appear first (higher severity). Example output (illustrative file paths):

```
Collateral findings: <count> issues in <count> other files

  CONCEPTUAL:
  docs/learned/planning/plan-sync-workflow.md:
    [OS] Describes the 5-step plan sync system — this was replaced by direct gateway calls in v0.9. Recommend: /local:audit-doc planning/plan-sync-workflow.md
  docs/learned/architecture/worker-delegation.md:
    [SF] Flow diagram shows 4 steps but code now has 6 (added validation + retry). Needs flow update.

  MECHANICAL:
  src/erk/core/subprocess.py:
    [SC] L45: Comment says "returns list" — actually returns dict. Fix: update comment.
  docs/learned/architecture/fail-open-patterns.md:
    [BX] "See also" link to planning/plan-schema.md — file renamed. Fix: update link.
```

If no collateral findings were recorded, omit this section entirely.

### Phase 8: Determine Action

**If `--auto-apply` mode is active:**

Automatically select the action based on the verdict without prompting:

- **KEEP** verdict → Proceed to Execute Actions with "Mark as audited (clean)"
- **NEEDS_UPDATE** verdict → Proceed to Execute Actions with "Apply accuracy fixes + stamp". Accuracy fixes MUST include removing VERBATIM code blocks identified in the Code Block Triage phase and replacing them with prose references.
- **SIMPLIFY / REPLACE WITH CODE REFS** verdict → Proceed to Execute Actions with "Mark as audited (with rewrite)" (apply rewrite + stamp)
- **CONSIDER DELETING** verdict → Proceed to Execute Actions with "Mark as audited (clean)" (stamp only, don't auto-delete)

**Collateral auto-apply:** If collateral findings exist, automatically fix mechanical source code issues (`STALE_COMMENT`, `STALE_DOCSTRING`) and broken links (`BROKEN_CROSS_REF`). Do NOT auto-apply conceptual findings (`OS`, `CF`, `SF`) or contradicting doc fixes (`CD`) — these require judgment. List unapplied findings in output as reminders.

**If `--auto-apply` mode is NOT active:**

Use AskUserQuestion to offer two groups of options:

**Primary document actions:**

- **"Apply recommended rewrite"** — rewrite the doc to remove duplicative content (only offer if verdict is SIMPLIFY or REPLACE WITH CODE REFS)
- **"Apply accuracy fixes"** — fix inaccurate claims, broken imports, renamed symbols (only offer if verification found INACCURATE/BROKEN claims but doc is otherwise valuable)
- **"Mark as audited (clean)"** — stamp frontmatter with audit date and `clean` result (use when verdict is KEEP)
- **"Mark as audited (with rewrite)"** — apply the rewrite AND stamp frontmatter (only offer if verdict is SIMPLIFY or REPLACE WITH CODE REFS)
- **"No action"** — just noting findings

**Collateral findings actions** (only shown if collateral findings exist):

- **"Apply mechanical fixes"** — fix stale comments, docstrings, and broken links in other files
- **"Apply all fixable collateral"** — mechanical fixes + contradicting doc fixes (conceptual findings always produce audit recommendations, not inline fixes)
- **"Skip collateral fixes"** — leave all collateral findings as-is

### Phase 9: Execute Actions

Based on the user's choice:

**If rewrite selected** (either "Apply recommended rewrite" or "Mark as audited (with rewrite)"):
Use the Edit tool to apply the recommended rewrite to the document.

**If audit stamp selected** (either "Mark as audited (clean)" or "Mark as audited (with rewrite)"):
Update the document's YAML frontmatter to add or update audit metadata:

```yaml
last_audited: "2026-02-05 12:45 PT"
audit_result: clean | edited
```

- Use `clean` when the audit found no significant issues (KEEP verdict, no rewrite applied)
- Use `edited` when the doc was rewritten to remove duplicative content

If the document already has `last_audited` / `audit_result` fields, overwrite them with the new values. Use the **current date and time in Pacific time, down to the minute**. Format: `YYYY-MM-DD HH:MM PT` (24-hour format, e.g., "2026-02-05 14:30 PT").

### Phase 10: Execute Collateral Fixes

If collateral fixes were selected (either via auto-apply or interactive choice):

**Mechanical fixes** (applied directly using the Edit tool):

1. `STALE_COMMENT` (SC) — Update the comment to match actual code behavior
2. `STALE_DOCSTRING` (SD) — Update the docstring to match actual signatures/behavior
3. `BROKEN_CROSS_REF` (BX) — Update the link to point to the correct file path
4. `CONTRADICTING_DOC` (CD) — Fix the specific contradicting claim (only when "Apply all fixable collateral" was chosen; skip ambiguous fixes with "needs manual review" note)

**Conceptual findings** (never auto-fixed — always produce recommendations):

- `OBSOLETE_SYSTEM` (OS): Output "Recommend: `/local:audit-doc <path>` — system described no longer exists"
- `CONCEPTUAL_DRIFT` (CF): Output "Recommend: `/local:audit-doc <path>` — concept meaning has changed"
- `STALE_FLOW` (SF): Output "Recommend: `/local:audit-doc <path>` — process flow outdated"

These are too significant for inline correction — they need their own full audit pass. The collateral finding's value is _discovery_, not repair.

Output summary of what was fixed, skipped, and recommended.

## Design Principles

1. **Adversarial framing**: Be skeptical of documentation value by default. The burden of proof is on the doc to justify its existence vs just reading code.

2. **Percentage-based scoring**: Show what % of the doc is duplicative or inaccurate for quick signal. A doc that's 80% duplicative is a strong candidate for simplification. Inaccurate content is treated as at least as severe as duplicative content in verdict calculations.

3. **Section-level granularity**: Don't just give a doc-level verdict. Show which sections add value and which don't, so the user can surgically edit.

4. **Concrete code references**: When flagging something as duplicative, always cite the specific source file and line that makes it redundant. This makes the audit actionable.

5. **Drift risk as separate axis**: Something can be non-duplicative today but high-risk for drift. Call this out separately.

6. **Collateral findings are opportunistic**: The audit reads source code and follows cross-references anyway. This is NOT a full audit of referenced files. Systemic problems warrant a separate `/local:audit-doc` invocation.

7. **Token cache value of reference material**: Third-party reference tables represent significant agent investment in fetching, parsing, and distilling external documentation. Discovered/undocumented API behavior is even more valuable — it cannot be re-acquired from any official source. Docs should not be penalized for containing external reference content when it serves as a token cache.
