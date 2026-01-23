---
description: Assess whether a PR or plan's work is already in master
---

# /local:check-relevance

Assesses whether a PR or plan's intended work is already represented in master, helping decide whether to close it.

## Usage

```bash
/local:check-relevance 2521              # Auto-detect PR or plan by issue number
/local:check-relevance --pr 2521         # Explicitly check a PR
/local:check-relevance --plan 2521       # Explicitly check a plan issue
```

---

## Agent Instructions

### Phase 1: Parse Input and Identify Type

Parse `$ARGUMENTS` to determine input:

**Step 1.1: Extract number and type**

- `--pr <number>`: Treat as PR
- `--plan <number>`: Treat as plan issue
- `<number>` only: Auto-detect (check for `erk-plan` label)

**Step 1.2: Auto-detect type (if not explicit)**

```bash
# Uses erk exec to avoid GraphQL rate limits
erk exec get-issue-body <NUMBER> | jq -r '.labels[]' | grep -q "erk-plan" && echo "plan" || echo "pr"
```

Store result as `ITEM_TYPE` (either `pr` or `plan`).

### Phase 2: Gather Context

**For PRs:**

```bash
# Get PR details
gh pr view <NUMBER> --json title,body,files,additions,deletions,commits,state,mergedAt,headRefName

# Get the diff
gh pr diff <NUMBER>
```

**For Plans:**

```bash
# Get plan issue body
erk exec get-issue-body <NUMBER>
```

Parse and store:

- **Title**: What is being implemented
- **Description**: Goals and context
- **Key identifiers**: Function names, class names, file paths mentioned
- **Expected changes**: What files/features should exist if implemented

### Phase 3: Understand Intent

From the gathered context, extract:

1. **Primary goal**: What is this PR/plan trying to accomplish?
2. **Key artifacts**: What files, functions, or classes would be created/modified?
3. **Feature signature**: Unique identifiers that would exist if implemented (function names, CLI commands, config keys, etc.)

Document your understanding:

```markdown
## Intent Analysis

**Goal**: [1-2 sentence summary of what this PR/plan aims to do]

**Expected artifacts**:

- File: `src/erk/foo.py` - new module for X
- Function: `do_thing()` in `src/erk/bar.py`
- CLI command: `erk thing`
```

### Phase 4: Search Master for Evidence

Search the current codebase (master/main) for evidence of the expected changes.

**Step 4.1: Check for expected files**

For each expected file path:

```bash
ls -la <expected_path> 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

**Step 4.2: Search for key identifiers**

For key function/class/command names:

```bash
# Use Grep tool to search
Grep(pattern="<function_name>", path="src/")
```

**Step 4.3: Search for related commits**

```bash
git log --oneline --all --grep="<relevant keywords>" | head -10
```

**Step 4.4: Search for related merged PRs**

```bash
gh pr list --state merged --search "<keywords from title>" --json number,title,mergedAt --limit 5
```

**Step 4.5: Check commit history for the branch (if PR)**

For PRs, check if the branch commits are already in master:

```bash
# Get commits using erk exec (avoids GraphQL rate limits)
erk exec get-pr-commits <NUMBER> | jq -r '.commits[].sha' | while read sha; do
  git branch --contains "$sha" 2>/dev/null | grep -qE '^\*?\s*master$' && echo "$sha: IN_MASTER" || echo "$sha: NOT_IN_MASTER"
done
```

### Phase 5: Create Evidence Table

Present findings in a structured table:

```markdown
## Evidence Table

| Expected              | Found in Master? | Evidence                                  |
| --------------------- | ---------------- | ----------------------------------------- |
| `src/erk/foo.py`      | YES              | File exists at path                       |
| `do_thing()` function | YES              | Found in `src/erk/bar.py:123`             |
| `erk thing` command   | NO               | CLI command not found                     |
| Related PR            | YES              | PR #1234 "Add thing feature" merged Jan 5 |
```

Calculate overlap:

- Count items found vs expected
- Note if found items are identical, similar, or different approach

### Phase 6: Determine Verdict

Based on the evidence, assign one of these verdicts:

| Verdict                   | Criteria                                                                |
| ------------------------- | ----------------------------------------------------------------------- |
| **SUPERSEDED**            | >80% of expected artifacts exist in master, with similar implementation |
| **PARTIALLY IMPLEMENTED** | 30-80% of expected artifacts exist, work is incomplete                  |
| **DIFFERENT APPROACH**    | Same goal achieved but via different implementation                     |
| **STILL RELEVANT**        | <30% exists, work is still needed                                       |
| **NEEDS REVIEW**          | Evidence is ambiguous, human judgment required                          |

**Decision logic:**

```
IF all_commits_in_master:
  verdict = SUPERSEDED (PR already merged or cherry-picked)
ELIF overlap >= 80% AND similar_implementation:
  verdict = SUPERSEDED
ELIF overlap >= 80% AND different_implementation:
  verdict = DIFFERENT_APPROACH
ELIF overlap >= 30%:
  verdict = PARTIALLY_IMPLEMENTED
ELIF overlap < 30%:
  verdict = STILL_RELEVANT
ELSE:
  verdict = NEEDS_REVIEW
```

### Phase 7: Present Assessment

Format the complete assessment:

```markdown
## Relevance Assessment for #<NUMBER>

**Type**: PR / Plan
**Title**: <title>
**State**: <open/closed/merged>

### Intent

<1-2 sentence summary>

### Evidence

<evidence table from Phase 5>

### Verdict: <VERDICT>

<Explanation of why this verdict was chosen>

### Recommendation

<Based on verdict, one of:>

- **Close**: This work is already in master. Safe to close.
- **Keep Open**: This work is still needed.
- **Review Manually**: Evidence is unclear, recommend human review of <specific items>.
- **Partial Close**: Consider closing and opening a new issue for remaining work: <list remaining items>
```

### Phase 8: Offer Actions

Use AskUserQuestion to let user decide:

**If verdict is SUPERSEDED or DIFFERENT_APPROACH:**

Options:

- "Close with comment explaining it's superseded"
- "Keep open for reference"
- "Let me review manually first"

**If verdict is PARTIALLY_IMPLEMENTED:**

Options:

- "Close and create new issue for remaining work"
- "Keep open and update description"
- "Let me review manually first"

**If verdict is STILL_RELEVANT:**

Options:

- "Mark as still relevant (no action)"
- "Add 'needs-attention' label"
- "Let me review manually first"

**If verdict is NEEDS_REVIEW:**

Options:

- "I'll review manually"
- "Show me more context"

### Phase 9: Execute Actions

Based on user selection:

**Close with comment:**

```bash
# For PRs
gh pr close <NUMBER> --comment "Closing: This work is already represented in master via <evidence>. See #<related_pr> for the merged implementation."

# For plans (uses erk exec to avoid GraphQL rate limits)
erk exec close-issue-with-comment <NUMBER> --comment "Closing: This work is already represented in master. <evidence>"
```

**Add label:**

```bash
gh api repos/dagster-io/erk/issues/<NUMBER>/labels -X POST -f "labels[]=<label>"
```

**Create follow-up issue:**

```bash
gh api repos/dagster-io/erk/issues -X POST \
  -f title="[Follow-up] <remaining work from #NUMBER>" \
  -f body="Follow-up from #<NUMBER> which was partially implemented.

## Remaining Work
<list of items not found in master>

## Original Context
See #<NUMBER> for original context."
```

Report the action taken and provide links to any new issues created.

---

## Error Handling

- If issue/PR not found, report error and stop
- If GitHub API rate limited, report and stop
- If unable to determine type, ask user to specify `--pr` or `--plan`
- If codebase search fails, note in evidence table and continue

## Notes

- Uses REST API where possible to avoid GraphQL rate limits
- Searches are performed on current master/main branch
- For large diffs, focuses on key files and function names rather than full content comparison
