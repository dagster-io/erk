---
description: Assess whether a PR or plan's work is already in master
---

# /local:check-superceded

Deep code-level analysis to determine if a PR's changes have been superseded by work already in master. Unlike simple metadata checks, this command reads actual file contents and compares implementation approaches.

## Usage

```bash
/local:check-superceded 2521           # Check PR #2521
```

---

## Agent Instructions

### Phase 1: Parse Input and Fetch PR Metadata

Parse `$ARGUMENTS` as a PR number.

```bash
gh pr view <NUMBER> --json title,body,state,headRefName,files
```

Store the title, body, state, branch name, and files list.

If the PR is already merged, report that and stop — merged PRs are not "superseded", they landed.

### Phase 2: Fetch PR Code Changes

Get the actual code diff — this is the primary evidence source.

```bash
# Get the full diff
gh pr diff <NUMBER>
```

**Large PR fallback:** If `gh pr diff` fails with HTTP 406 (PR has 300+ files), use the REST API instead:

```bash
gh api --paginate --jq '.[].filename' "repos/{owner}/{repo}/pulls/<NUMBER>/files"
```

Then read each file individually from master and the PR branch to compare.

Also get the changed files list:

```bash
gh pr view <NUMBER> --json files --jq '.files[].path'
```

### Phase 3: Understand PR Intent

From the diff and PR description, extract and document:

```markdown
## Intent Analysis

**Primary goal**: [What is this PR trying to accomplish?]

**Key code changes**:

- [New functions, modified logic, new files, new CLI options]
- [Unique identifiers that would exist if this work landed]

**Feature signatures**:

- [Function names, class names, CLI commands, config keys unique to this PR]
```

### Phase 4: Deep Code Comparison

**CRITICAL DIRECTIVE:** You MUST read the actual file contents on master for every file the PR modifies. Do not rely on grep hits or file existence alone. Compare the PR's diff hunks against the current master code to determine if the intended changes are present.

Steps:

1. **For each file modified by the PR that exists on master**: Read it with the `Read` tool. Compare the PR's changes against what's currently in that file.
2. **For each new file the PR creates**: Search master for equivalent functionality — grep for key identifiers from the diff, then read any matching files to compare implementation approach.
3. **For each deleted file**: Verify it's still absent on master (or was re-added).
4. **Per-file implementation comparison**:
   - Does the same function/class exist in master?
   - Does it achieve the same goal?
   - Is it the same implementation or a different approach?
5. **Also read any docs the PR modifies/creates** and compare against current docs on master.

### Phase 5: Supporting Context (metadata — informative only)

These signals support but do NOT determine the verdict:

```bash
# Related merged PRs
gh pr list --state merged --search "<keywords>" --limit 5 --json number,title,mergedAt

# Recent related commits
git log --oneline -20 --grep="<keyword>"
```

**Explicitly excluded as primary evidence:** commit SHA checks, commit message matching, file existence alone.

### Phase 6: Build Evidence Table

Present per-file analysis:

```markdown
## Evidence Table

| File / Change               | Master State    | Match Type         | Detail                                            |
| --------------------------- | --------------- | ------------------ | ------------------------------------------------- |
| `src/erk/foo.py` (modified) | Read & compared | EQUIVALENT         | Same function exists with minor style differences |
| `src/erk/bar.py` (new file) | Searched master | DIFFERENT_APPROACH | Same goal achieved via `baz.py` instead           |
| `src/erk/old.py` (deleted)  | Verified absent | IDENTICAL          | File was already removed                          |
```

**Match Types:**

- **IDENTICAL** — same code exists in master
- **EQUIVALENT** — same goal, similar approach, minor differences
- **DIFFERENT_APPROACH** — same goal achieved via different implementation
- **PARTIAL** — some aspects present, others missing
- **ABSENT** — not in master at all

### Phase 7: Determine Verdict

| Verdict                  | Criteria                                                              |
| ------------------------ | --------------------------------------------------------------------- |
| **SUPERSEDED**           | All key changes are IDENTICAL/EQUIVALENT/DIFFERENT_APPROACH in master |
| **PARTIALLY_SUPERSEDED** | Some key changes present, others still needed                         |
| **STILL_RELEVANT**       | Most key changes are ABSENT from master                               |
| **NEEDS_REVIEW**         | Evidence is ambiguous — cannot determine confidently                  |

### Phase 8: Present Assessment and Offer Actions

Format the complete assessment:

```markdown
## Superseded Assessment for PR #<NUMBER>

**Title**: <title>
**State**: <open/closed/merged>
**Branch**: <branch name>

### Intent

<1-2 sentence summary of what this PR aims to do>

### Evidence

<Evidence table from Phase 6>

### Verdict: <VERDICT>

<Explanation of why this verdict was chosen, referencing specific files and match types>

### Recommendation

<Based on verdict, recommended action>
```

Then use `AskUserQuestion` with options based on verdict:

**If SUPERSEDED:**

- "Close with comment explaining superseded status"
- "Keep open for reference"
- "Review manually"

**If PARTIALLY_SUPERSEDED:**

- "Close and note remaining work"
- "Keep open"
- "Review manually"

**If STILL_RELEVANT:**

- "Mark as still relevant (no action)"
- "Review manually"

**If NEEDS_REVIEW:**

- "I'll review manually"
- "Show me more context"

### Phase 9: Execute Chosen Action

Based on user selection:

**Close with comment:**

```bash
gh pr close <NUMBER> --comment "Closing as superseded: This work is already represented in master.

## Evidence Summary
<brief evidence table or key findings>

Assessment performed by /local:check-superceded"
```

**Keep open or review manually:** No automated action — just confirm.

---

## Error Handling

- If PR not found: report error and stop
- If `gh pr diff` fails with HTTP 406: fall back to REST API file listing
- If GitHub API rate limited: report and stop
