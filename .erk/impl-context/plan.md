# Documentation Plan: Add erk exec get-pr-view command to avoid GraphQL rate limits

## Context

This plan addresses documentation gaps from PR #7793, which introduced `erk exec get-pr-view` - a REST API-based command for fetching PR metadata. The command was created to solve a critical workflow problem: GitHub's GraphQL API has stricter rate limits than REST, and commands/skills that call `gh pr view` frequently were causing rate limit exhaustion that blocked agent workflows.

The implementation migrated four commands and one skill from `gh pr view` to the new REST-based alternative, establishing a new best practice for PR metadata fetching in erk. Documentation is needed to prevent future agents from reintroducing the problematic `gh pr view` pattern and to help them understand when and how to use the new command.

The key insight worth preserving is the non-obvious relationship between `gh pr view` and GraphQL rate limits - this is implementation detail of the GitHub CLI that agents would not naturally discover. A tripwire is warranted to catch this pattern before it causes workflow failures.

## Raw Materials

PR #7793

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 4 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 1 |
| Potential tripwires (score 2-3) | 0 |

## Documentation Items

### HIGH Priority

#### 1. Add tripwire to github-api-rate-limits.md

**Location:** `docs/learned/architecture/github-api-rate-limits.md`
**Action:** UPDATE
**Source:** [PR #7793]

**Draft Content:**

```markdown
## Tripwire: gh pr view Uses GraphQL

**CRITICAL: Use `erk exec get-pr-view` instead of `gh pr view` for PR metadata in commands/skills.**

The `gh pr view --json` command uses the GraphQL API, which has stricter (and separately tracked) rate limits from the REST API. When commands or skills call `gh pr view` frequently, GraphQL rate limits become exhausted while REST limits remain available, blocking agent workflows unnecessarily.

**When fetching PR metadata:**
- Use: `erk exec get-pr-view <pr-number> | jq -r '.<field>'`
- Avoid: `gh pr view <pr-number> --json <fields> -q '...'`

The `erk exec get-pr-view` command uses the REST API and supports three lookup modes:
1. Explicit PR number: `erk exec get-pr-view 123`
2. Explicit branch: `erk exec get-pr-view --branch feature-x`
3. Auto-detect from HEAD: `erk exec get-pr-view` (no args)

See `docs/learned/integrations/github-rest-api-pr-view.md` for full documentation.
```

#### 2. Create github-rest-api-pr-view.md

**Location:** `docs/learned/integrations/github-rest-api-pr-view.md`
**Action:** CREATE
**Source:** [PR #7793]

**Draft Content:**

```markdown
---
read-when:
  - fetching PR metadata in commands or skills
  - encountering GraphQL rate limit errors
  - working on GitHub integration code
  - authoring new erk commands that need PR information
---

# REST API-Based PR View Command

## Problem

The `gh pr view --json` command uses GitHub's GraphQL API, which has stricter rate limits than the REST API. When agent commands or skills fetch PR metadata frequently, GraphQL limits exhaust while REST limits remain available, causing workflow failures.

## Solution

The `erk exec get-pr-view` command provides REST API-based PR metadata fetching with three lookup modes.

## Usage

**By PR number:**
```bash
erk exec get-pr-view 123
```

**By branch name:**
```bash
erk exec get-pr-view --branch feature-x
```

**Auto-detect from HEAD:**
```bash
erk exec get-pr-view
```

## Output

Returns JSON with comprehensive PR metadata. Parse with jq:

```bash
# Get PR body
erk exec get-pr-view 123 | jq -r '.body'

# Get PR state
erk exec get-pr-view 123 | jq -r '.state'

# Get head branch name
erk exec get-pr-view 123 | jq -r '.head_ref_name'
```

## Migration Examples

| Before | After |
|--------|-------|
| `gh pr view "$pr" --json body --jq '.body'` | `erk exec get-pr-view "$pr" \| jq -r '.body'` |
| `gh pr view --json headRefName -q '.headRefName'` | `erk exec get-pr-view \| jq -r '.head_ref_name'` |

## Exit Codes

- 0: Success
- 1: PR not found or no branch detected

## Source

See `src/erk/cli/commands/exec/scripts/get_pr_view.py` for implementation.
```

### MEDIUM Priority

#### 3. Update erk-exec-commands.md inventory

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [PR #7793]

**Draft Content:**

Add to the PR Operations section:

```markdown
- `get-pr-view` - Fetch PR metadata via REST API (avoids GraphQL rate limits). Supports lookup by PR number, branch name, or auto-detect from HEAD.
```

#### 4. Create JSON schema reference

**Location:** `docs/learned/reference/pr-view-json-schema.md`
**Action:** CREATE
**Source:** [PR #7793]

**Draft Content:**

```markdown
---
read-when:
  - parsing erk exec get-pr-view output
  - building tools that consume PR metadata
---

# PR View JSON Schema

Output schema for `erk exec get-pr-view` command.

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `number` | int | PR number |
| `title` | string | PR title |
| `body` | string | PR description |
| `state` | string | PR state (open, closed, merged) |
| `url` | string | PR URL |
| `author` | string | PR author username |
| `labels` | array | List of label names |
| `head_ref_name` | string | Source branch name |
| `base_ref_name` | string | Target branch name |
| `mergeable` | bool | Whether PR can be merged |
| `merge_state_status` | string | Merge state (clean, blocked, etc.) |
| `is_cross_repository` | bool | Whether PR is from a fork |
| `created_at` | string | ISO timestamp of creation |
| `updated_at` | string | ISO timestamp of last update |

## jq Examples

```bash
# Get labels as comma-separated list
erk exec get-pr-view 123 | jq -r '.labels | join(",")'

# Check if PR is mergeable
erk exec get-pr-view 123 | jq -r '.mergeable'

# Get author and title
erk exec get-pr-view 123 | jq -r '"\(.author): \(.title)"'
```

## Source

See `src/erk/cli/commands/exec/scripts/get_pr_view.py` for implementation details.
```

## Contradiction Resolutions

None. All existing documentation is consistent with the new implementation.

## Stale Documentation Cleanup

None. All referenced files in existing documentation were verified to exist.

## Prevention Insights

No errors or failed approaches were discovered during implementation. Both analyzed sessions completed successfully without any blocking issues. The implementation followed established patterns and the PR received no substantive review feedback.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Using gh pr view in commands/skills causes GraphQL rate limit exhaustion

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before using `gh pr view` in commands or skills

**Warning:** Use `erk exec get-pr-view` instead. `gh pr view` uses GraphQL which has separate (often exhausted) rate limits. REST-based alternative prevents workflow blocking. Supports three modes: by PR number, by branch name, or auto-detect from HEAD. See docs/learned/integrations/github-rest-api-pr-view.md

**Target doc:** `docs/learned/architecture/github-api-rate-limits.md`

This tripwire is warranted because:

1. **Non-obvious**: Nothing in `gh pr view` documentation or behavior suggests it uses GraphQL rather than REST. Agents would not naturally discover this without experiencing rate limit failures.

2. **Cross-cutting**: The pattern affects any command or skill that fetches PR metadata. This PR migrated 4 commands and 1 skill, demonstrating the widespread impact.

3. **Silent failure mode**: When GraphQL limits are exhausted, commands fail with opaque API errors. There's no clear indication that REST calls would still work. This causes entire workflows to block unnecessarily.

The trigger pattern `gh\s+pr\s+view` can be matched in commands and skills to warn agents before they introduce this anti-pattern.

## Potential Tripwires

None (no items in score 2-3 range).
