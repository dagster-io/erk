# Plan: PR State Validation and Branch Collision Detection

## Problem Statement

The `gh pr ready` step fails when a PR is already closed/merged, producing a cryptic error. Additionally, branch names derived from issue titles can collide between different issues.

**Concrete example (Issue #1345):**
- Issue #1338 "Convert SystemExit to Ensure Call" → branch `convert-systemexit-to-ensure-c` → PR #1339 (CLOSED)
- Issue #1345 "Convert SystemExit to Ensure Call" (same title) → derived same branch name
- Workflow reused branch → tried `gh pr ready` on closed PR #1339 → **cryptic failure**

**User requirements:**
1. Client-side check in `erk submit` - fail before triggering workflow
2. Early CI check in setup job - fail fast with clear messaging
3. Better error at `gh pr ready` step - defense in depth
4. Detect branch name collisions with other issues

## Defense-in-Depth Strategy

### Layer 1: Client-Side Validation (`erk submit`)

**File:** `src/erk/cli/commands/submit.py`

**Required Changes to GitHub ABC:**

First, extend the GitHub abstraction to support getting PR info with linked issue. Add to `packages/erk-shared/src/erk_shared/github/abc.py`:

```python
@dataclass(frozen=True)
class PRDetailedInfo:
    """Detailed PR information including linked issues."""
    
    number: int
    state: str  # "OPEN", "MERGED", "CLOSED"
    linked_issue_number: int | None  # From closingIssuesReferences
    branch_name: str
```

Add new abstract method:

```python
@abstractmethod
def get_pr_for_branch(self, repo_root: Path, branch: str) -> PRDetailedInfo | None:
    """Get detailed PR information for a branch, including linked issue.
    
    Uses GitHub's closingIssuesReferences to find the issue that this PR closes.
    
    Args:
        repo_root: Repository root directory
        branch: Branch name to query
        
    Returns:
        PRDetailedInfo with state and linked issue, or None if no PR exists
    """
    ...
```

**Implementation in RealGitHub:**

Use GraphQL to query PR with `closingIssuesReferences`:

```graphql
query($owner: String!, $repo: String!, $branch: String!) {
  repository(owner: $owner, name: $repo) {
    pullRequests(headRefName: $branch, first: 1) {
      nodes {
        number
        state
        closingIssuesReferences(first: 1) {
          nodes {
            number
          }
        }
      }
    }
  }
}
```

**Changes to submit.py:**

After line 88 (after issue.state != "OPEN" check), add:

```python
# Derive branch name from issue title (same logic as workflow)
branch_name = _derive_branch_name(issue.title)

# Check if a PR exists for this branch
pr_info = ctx.github.get_pr_for_branch(repo.root, branch_name)

if pr_info is not None:
    # Check for branch collision (different issue)
    if pr_info.linked_issue_number is not None and pr_info.linked_issue_number != issue_number:
        user_output(
            click.style("Error: ", fg="red")
            + f"Branch '{branch_name}' is associated with issue #{pr_info.linked_issue_number}\n\n"
            f"This issue (#{issue_number}) would derive the same branch name.\n"
            "Please rename one of the issues to avoid collision."
        )
        raise SystemExit(1)

    # Check PR state
    if pr_info.state in ("CLOSED", "MERGED"):
        user_output(
            click.style("Error: ", fg="red")
            + f"PR for branch '{branch_name}' is {pr_info.state}\n\n"
            f"Cannot submit to a {pr_info.state.lower()} PR.\n"
            "Options:\n"
            f"  - Reopen the PR: gh pr reopen {branch_name}\n"
            f"  - Delete the branch and retry: git push origin --delete {branch_name}"
        )
        raise SystemExit(1)
```

**Helper function to add:**

```python
import re

def _derive_branch_name(issue_title: str) -> str:
    """Derive branch name from issue title (matches workflow logic).
    
    Must exactly match the bash logic in dispatch-erk-queue.yml:
    - tr '[:upper:]' '[:lower:]'  -> lowercase
    - sed 's/[^a-z0-9-]/-/g'      -> non-alphanum to hyphen
    - sed 's/--*/-/g'             -> collapse multiple hyphens
    - sed 's/^-//'                -> remove leading hyphen
    - sed 's/-$//'                -> remove trailing hyphen
    - ${BRANCH_NAME:0:30}         -> truncate to 30 chars
    - sed 's/-$//'                -> remove trailing hyphen again
    """
    branch = issue_title.lower()
    branch = re.sub(r'[^a-z0-9-]', '-', branch)
    branch = re.sub(r'-+', '-', branch)  # collapse multiple hyphens
    branch = branch.strip('-')
    branch = branch[:30]
    branch = branch.rstrip('-')  # remove trailing hyphen after truncation
    return branch
```

### Layer 2: Workflow Setup Validation

**Files:**
- `.github/workflows/dispatch-erk-queue.yml` (after line 319, before "Create draft PR")
- `.github/workflows/dispatch-erk-queue-single-job.yml` (after line 252, before "Create draft PR")

Add new step "Validate PR state":

```yaml
- name: Validate PR state
  id: validate_pr
  env:
    ISSUE_NUMBER: ${{ steps.set_issue.outputs.issue_number }}
    BRANCH_NAME: ${{ steps.branch_name.outputs.branch_name }}
    GH_TOKEN: ${{ github.token }}
  run: |
    # Check if PR exists for this branch
    if gh pr view "$BRANCH_NAME" --json number,state,body &> /dev/null; then
      PR_STATE=$(gh pr view "$BRANCH_NAME" --json state -q .state)
      
      # Use GitHub's closingIssuesReferences via GraphQL
      LINKED_ISSUE=$(gh api graphql -f query='
        query($owner: String!, $repo: String!, $branch: String!) {
          repository(owner: $owner, name: $repo) {
            pullRequests(headRefName: $branch, first: 1) {
              nodes {
                closingIssuesReferences(first: 1) {
                  nodes { number }
                }
              }
            }
          }
        }' -f owner="${GITHUB_REPOSITORY_OWNER}" \
           -f repo="${GITHUB_REPOSITORY#*/}" \
           -f branch="$BRANCH_NAME" \
           --jq '.data.repository.pullRequests.nodes[0].closingIssuesReferences.nodes[0].number // empty')

      # Check for branch collision
      if [ -n "$LINKED_ISSUE" ] && [ "$LINKED_ISSUE" != "$ISSUE_NUMBER" ]; then
        gh issue comment "$ISSUE_NUMBER" --body "**Branch Collision Detected**

Branch \`$BRANCH_NAME\` is already associated with issue #$LINKED_ISSUE.

This issue (#$ISSUE_NUMBER) derives the same branch name from its title.

**Resolution:** Rename one of the issues to generate a unique branch name."
        exit 1
      fi

      # Check PR state
      if [ "$PR_STATE" = "CLOSED" ] || [ "$PR_STATE" = "MERGED" ]; then
        gh issue comment "$ISSUE_NUMBER" --body "**PR Already ${PR_STATE}**

The PR for branch \`$BRANCH_NAME\` has been ${PR_STATE,,}.

Cannot submit implementation to a ${PR_STATE,,} PR.

**Options:**
- Reopen the PR: \`gh pr reopen $BRANCH_NAME\`
- Delete branch and retry: \`git push origin --delete $BRANCH_NAME\`"
        exit 1
      fi

      echo "PR exists and is OPEN (state: $PR_STATE)"
    else
      echo "No existing PR for branch $BRANCH_NAME"
    fi
```

### Layer 3: Improved `gh pr ready` Step

**Files:**
- `.github/workflows/dispatch-erk-queue.yml` (lines 567-575)
- `.github/workflows/dispatch-erk-queue-single-job.yml` (lines 405-412)

Replace the existing step with idempotent version:

```yaml
- name: Mark PR ready for review
  if: steps.implement.outputs.implementation_success == 'true'
  env:
    GH_TOKEN: ${{ github.token }}
    BRANCH_NAME: ${{ needs.setup.outputs.branch_name }}
    ISSUE_NUMBER: ${{ needs.setup.outputs.issue_number }}
  run: |
    # Get PR state and draft status
    PR_INFO=$(gh pr view "$BRANCH_NAME" --json state,isDraft 2>/dev/null || echo '{}')
    PR_STATE=$(echo "$PR_INFO" | jq -r '.state // "NONE"')
    IS_DRAFT=$(echo "$PR_INFO" | jq -r '.isDraft // false')

    if [ "$PR_STATE" = "NONE" ]; then
      echo "No PR found for branch $BRANCH_NAME"
      gh issue comment "$ISSUE_NUMBER" --body "**Mark Ready Failed**

No PR found for branch \`$BRANCH_NAME\`. This is unexpected after successful implementation.

Please investigate the workflow logs."
      exit 1
    fi

    if [ "$PR_STATE" = "CLOSED" ] || [ "$PR_STATE" = "MERGED" ]; then
      echo "PR is $PR_STATE - cannot mark ready"
      gh issue comment "$ISSUE_NUMBER" --body "**Mark Ready Failed**

PR for branch \`$BRANCH_NAME\` is **$PR_STATE**.

Implementation succeeded but cannot mark a $PR_STATE PR as ready for review.

**This should have been caught earlier.** Please report this as a bug."
      exit 1
    fi

    if [ "$IS_DRAFT" = "false" ]; then
      echo "PR is already ready for review (not draft)"
    else
      gh pr ready "$BRANCH_NAME"
      echo "PR marked ready for review"
    fi
```

## Implementation Order

1. **Layer 1 first (client)** - Start with `erk submit` validation for better local UX
   - Add `PRDetailedInfo` dataclass to types.py
   - Add `get_pr_for_branch()` to GitHub ABC
   - Implement in RealGitHub using GraphQL
   - Add to FakeGitHub with constructor parameter
   - Add `_derive_branch_name()` helper to submit.py
   - Add validation logic to submit_cmd
   - Write tests

2. **Layer 2 second (workflow)** - Add setup job validation as defense in depth
   - Add "Validate PR state" step to dispatch-erk-queue.yml
   - Add same step to dispatch-erk-queue-single-job.yml

3. **Layer 3 third (gh pr ready)** - Improve error handling as final safety net
   - Update "Mark PR ready" step in both workflows

## Files to Modify

| File | Changes |
|------|---------|
| `packages/erk-shared/src/erk_shared/github/types.py` | Add `PRDetailedInfo` dataclass |
| `packages/erk-shared/src/erk_shared/github/abc.py` | Add `get_pr_for_branch()` abstract method |
| `packages/erk-shared/src/erk_shared/github/real.py` | Implement `get_pr_for_branch()` with GraphQL |
| `src/erk/core/github/fake.py` | Add `get_pr_for_branch()` fake implementation |
| `src/erk/cli/commands/submit.py` | Add `_derive_branch_name()`, PR state validation |
| `.github/workflows/dispatch-erk-queue.yml` | Add "Validate PR state" step, update "Mark PR ready" step |
| `.github/workflows/dispatch-erk-queue-single-job.yml` | Same changes as above |
| `tests/commands/test_submit.py` | Add tests for PR state validation and branch collision |

## Testing Strategy

**Unit tests for submit.py:**
- Test `_derive_branch_name()` matches workflow logic with various inputs
- Test closed PR detection blocks submission
- Test merged PR detection blocks submission
- Test branch collision detection (PR linked to different issue)
- Test happy path (no PR exists)
- Test happy path (PR exists and is OPEN, linked to same issue)

**FakeGitHub extension:**
- Add `pr_detailed_infos: dict[str, PRDetailedInfo]` constructor parameter
- Return configured data from `get_pr_for_branch()`

**Manual workflow testing:**
1. Submit issue where PR is closed → should fail in setup
2. Submit issue where PR is merged → should fail in setup
3. Submit two issues with same derived branch name → should fail with collision error

---

## Enrichment Details

### Process Summary

- **Mode**: enriched
- **Guidance applied**: yes (GitHub API usage)
- **Questions asked**: 2
- **Context categories extracted**: 7 of 8

### Clarifications Made

1. **GitHub API approach**: Use `ctx.github` abstraction with a new `get_pr_for_branch()` method using GraphQL `closingIssuesReferences` instead of regex parsing PR body.

2. **Issue linkage extraction**: Use GitHub's official API (`closingIssuesReferences` GraphQL field) rather than regex parsing of PR body text.

### Context Categories Populated

- [x] API/Tool Quirks
- [x] Architectural Insights
- [x] Domain Logic & Business Rules
- [x] Complex Reasoning
- [x] Known Pitfalls
- [x] Raw Discoveries Log
- [x] Planning Artifacts
- [ ] Implementation Risks (none significant)

### API/Tool Quirks

- **GitHub GraphQL `closingIssuesReferences`**: This field provides the official way to get issues linked to a PR via closing keywords. It's more reliable than parsing PR body text with regex.
- **`gh pr view` by branch name**: The gh CLI supports querying PRs by branch name directly (`gh pr view BRANCH_NAME`), not just PR number.
- **PR state values**: GitHub uses uppercase states: "OPEN", "CLOSED", "MERGED". The workflow uses lowercase in some bash logic (`${PR_STATE,,}` for lowercase conversion).

### Architectural Insights

- **Three-layer dependency injection pattern**: The codebase uses Real/DryRun/Fake implementations for all external integrations. New GitHub methods must be added to all three implementations.
- **GitHub ABC lives in `erk-shared` package**: The GitHub abstraction is in the shared package (`packages/erk-shared/src/erk_shared/github/`) because it's used by multiple packages.
- **FakeGitHub uses constructor injection**: All test state is provided via constructor parameters, not setter methods. New methods need corresponding constructor parameters.
- **Branch name derivation logic is duplicated**: The workflow has bash logic to derive branch names from issue titles. This must be exactly replicated in Python for the client-side check.

### Known Pitfalls

- **Branch name derivation must match exactly**: If the Python implementation derives a different branch name than the bash workflow, the validation will fail to catch collisions. Critical to test edge cases (unicode, special characters, trailing hyphens after truncation).
- **GraphQL field names are camelCase**: GitHub's GraphQL API uses `closingIssuesReferences`, not `closing_issues_references`. Python code accessing the response must use camelCase keys.
- **`jq -r '.state // "NONE"'` syntax**: The `//` operator in jq provides a default value. Empty string is different from `null`.
- **PR state is not the same as issue state**: PRs can be CLOSED while the linked issue is still OPEN. Don't confuse them.
