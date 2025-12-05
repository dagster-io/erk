# Plan Lifecycle Architecture Improvements

## Implementation Status

- [ ] **Improvement 1:** Unify `.worker-impl/` and `.impl/`
- [ ] **Improvement 2:** Replace `distinct_id` with comment-based run discovery
- [ ] **Improvement 3:** Consolidate metadata block types
- [x] **Improvement 4:** Use GitHub's native branch-to-issue linking
- [ ] **Improvement 5:** Store plan in issue body (not split)
- [ ] **Improvement 6:** Let workflow create PR

---

This document outlines proposed simplifications to the plan lifecycle system. These improvements reduce complexity, eliminate redundant mechanisms, and leverage GitHub's native features.

## Overview

The current plan lifecycle has evolved organically and accumulated several layers of indirection:

| Current State                          | Proposed State                           |
| -------------------------------------- | ---------------------------------------- |
| 6 metadata block types                 | 3 metadata block types                   |
| `.worker-impl/` + `.impl/` duality     | Single `.impl/` reconstructed from issue |
| Custom `distinct_id` for run discovery | Comment-based run discovery              |
| Custom branch name derivation          | GitHub's native issue-to-branch linking  |
| Split storage (body + comment)         | Single issue body storage                |
| Local draft PR creation                | Workflow-created PR                      |

---

## Improvement 1: Unify `.worker-impl/` and `.impl/`

### Current State

Two folders serve nearly identical purposes:

| Folder          | Git Status              | Purpose                                      |
| --------------- | ----------------------- | -------------------------------------------- |
| `.worker-impl/` | Committed, then deleted | Remote implementation (GitHub Actions)       |
| `.impl/`        | In `.gitignore`         | Local implementation + Claude's working copy |

**Current workflow:**

1. `erk submit` creates `.worker-impl/` and commits it
2. Workflow checks out branch with `.worker-impl/`
3. Workflow copies `.worker-impl/` → `.impl/`
4. Claude reads from `.impl/`
5. After implementation, workflow deletes `.worker-impl/` in separate commit

**Problems:**

- Cognitive overhead: two folders doing the same thing
- Copy step adds complexity (Phase 4 Step 1)
- Cleanup commit pollutes git history
- `.worker-impl/` briefly exists in git history

### Proposed State

**Reconstruct `.impl/` from the issue** - The issue already contains the complete plan in `plan-body`. The workflow can reconstruct `.impl/` fresh:

```bash
# Early in workflow, before Claude runs
erk plan reconstruct --issue $ISSUE_NUMBER --output .impl/
```

This command would:

1. Fetch issue via `gh issue view $ISSUE_NUMBER`
2. Parse `plan-body` metadata block
3. Write `plan.md` to `.impl/`
4. Generate initial `progress.md` with all steps unchecked
5. Create `issue.json` with issue reference
6. Create `run-info.json` with workflow run details

**Benefits:**

- Eliminates `.worker-impl/` entirely
- No committed artifacts to clean up
- Issue becomes the single source of truth
- `erk submit` becomes simpler (just dispatch, no file creation)
- Local workflow unchanged (`.impl/` stays gitignored)

### Implementation Notes

**New command: `erk plan reconstruct`**

```python
@app.command()
def reconstruct(
    issue_number: int,
    output: Path = Path(".impl"),
) -> None:
    """Reconstruct .impl/ folder from GitHub issue."""
    # Fetch issue
    issue = github.get_issue(issue_number)

    # Extract plan content from plan-body metadata block
    plan_content = extract_plan_body(issue.comments[0])

    # Create .impl/ structure
    create_impl_folder(output, plan_content)
    save_issue_reference(output, issue_number, issue.url)
```

**Workflow changes:**

```yaml
# Before (current)
- name: Copy .worker-impl to .impl
  run: |
    cp -r .worker-impl/ .impl/

# After (proposed)
- name: Reconstruct .impl from issue
  run: |
    erk plan reconstruct --issue ${{ inputs.issue_number }}
```

---

## Improvement 2: Replace `distinct_id` with Comment-Based Run Discovery

### Current State

A 6-character base36 identifier (`distinct_id`) is generated at dispatch time to enable finding the specific workflow run:

```python
def generate_distinct_id() -> str:
    """Generate 6-char base36 identifier for workflow run discovery."""
    return base36_encode(random.randint(0, 36**6 - 1)).zfill(6)
```

**Current workflow:**

1. `erk submit` generates `distinct_id` (e.g., `abc123`)
2. Passes `distinct_id` to workflow dispatch as input
3. Workflow sets `run-name: "${{ inputs.issue_number }}:${{ inputs.distinct_id }}"`
4. Submitter polls `gh run list` looking for `displayTitle` containing `:abc123`
5. Once found, extracts `run_id` from matching run

**Problems:**

- Custom identifier system for something GitHub already provides
- Polling workflow list is inefficient (returns many runs)
- Race condition: run may not appear immediately in list
- `distinct_id` adds complexity to dispatch inputs
- Must match by string parsing of `displayTitle`

### Proposed State

**Have the workflow post its `run_id` to the issue as its first action.** The submitter polls for that comment instead:

```yaml
# First step in workflow
- name: Post run info to issue
  run: |
    gh issue comment ${{ inputs.issue_number }} --body "$(cat <<EOF
    <!-- erk:metadata-block:workflow-run -->
    <details>
    <summary><code>workflow-run</code></summary>

    \`\`\`yaml
    run_id: "${{ github.run_id }}"
    run_url: "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    \`\`\`

    </details>
    <!-- /erk:metadata-block:workflow-run -->
    EOF
    )"
```

**Submitter polling:**

```python
def wait_for_workflow_run(issue_number: int, timeout: int = 300) -> str:
    """Wait for workflow to post its run_id to the issue."""
    start = time.time()
    while time.time() - start < timeout:
        comments = github.get_issue_comments(issue_number)
        for comment in reversed(comments):  # Check newest first
            if "erk:metadata-block:workflow-run" in comment.body:
                return extract_run_id(comment.body)
        time.sleep(5)
    raise TimeoutError(f"Workflow did not start within {timeout}s")
```

**Benefits:**

- Eliminates custom `distinct_id` generation
- Simpler dispatch (fewer inputs)
- More reliable discovery (comment is authoritative)
- No string matching on `displayTitle`
- Run info persisted on issue for debugging
- Leverages existing metadata block infrastructure

### Implementation Notes

**Changes to `erk submit`:**

```python
# Before
distinct_id = generate_distinct_id()
dispatch_workflow(
    inputs={
        "issue_number": issue_number,
        "distinct_id": distinct_id,  # Remove this
        ...
    }
)
run_id = poll_for_run_by_distinct_id(distinct_id)

# After
dispatch_workflow(
    inputs={
        "issue_number": issue_number,
        ...
    }
)
run_id = wait_for_workflow_run(issue_number)
```

**Workflow changes:**

```yaml
# Before
name: Implement Issue ${{ inputs.issue_number }}:${{ inputs.distinct_id }}

# After
name: Implement Issue ${{ inputs.issue_number }}

# Add as first step:
- name: Post run info to issue
  run: |
    gh issue comment ${{ inputs.issue_number }} --body "..."
```

**Files to modify:**

- `src/erk/cli/commands/submit.py` - Remove `distinct_id` generation and polling
- `.github/workflows/dispatch-erk-queue-git.yml` - Add comment posting, remove from run-name
- `packages/erk-shared/src/erk_shared/distinct_id.py` - Delete (no longer needed)

---

## Improvement 3: Consolidate Metadata Block Types

### Current State

Six different metadata block schemas:

| Block Key                   | Location            | Purpose               |
| --------------------------- | ------------------- | --------------------- |
| `plan-header`               | Issue body          | Plan metadata         |
| `plan-body`                 | Issue first comment | Full plan content     |
| `submission-queued`         | Issue comment       | Marks submission      |
| `workflow-started`          | Issue comment       | Links to workflow run |
| `erk-implementation-status` | Issue comment       | Progress updates      |
| `erk-worktree-creation`     | Issue comment       | Local worktree docs   |

**Problems:**

- `submission-queued` and `workflow-started` are nearly identical (status transitions)
- `erk-implementation-status` duplicates info already in `progress.md`
- Multiple places to look for status information
- Parsing complexity for each schema

### Proposed State

Three block types with clear responsibilities:

| Block Key         | Location              | Purpose                       |
| ----------------- | --------------------- | ----------------------------- |
| `plan-header`     | Issue body            | Plan metadata (unchanged)     |
| `plan-body`       | Issue body or comment | Full plan content             |
| `dispatch-status` | Issue comment         | All dispatch lifecycle states |

**`dispatch-status` schema:**

```yaml
schema: dispatch-status
status: queued | started | in_progress | complete | failed
timestamp: 2025-01-15T10:30:00Z
submitted_by: username # Set at queue time
workflow_run_id: "1234567890" # Set when started
workflow_run_url: https://... # Set when started
branch_name: feature-25-01-15 # Set when started
completed_steps: 3 # Updated during progress
total_steps: 5 # Updated during progress
```

**Status transitions:**

```
queued → started → in_progress → complete
                              ↘ failed
```

**Single comment, updated in place** rather than multiple comments:

```python
def update_dispatch_status(issue_number: int, status: str, **fields) -> None:
    """Update or create dispatch-status comment."""
    comment = find_dispatch_status_comment(issue_number)
    if comment:
        # Update existing
        update_metadata_block(comment, "dispatch-status", status=status, **fields)
    else:
        # Create new
        post_metadata_comment(issue_number, "dispatch-status", status=status, **fields)
```

**Benefits:**

- Single place to check dispatch status
- Fewer parsing functions to maintain
- Cleaner issue comment history
- Simpler mental model

---

## Improvement 4: Use GitHub's Native Branch-to-Issue Linking

### Current State

Custom branch naming with deterministic derivation:

```python
def derive_branch_name_with_date(issue_title: str) -> str:
    """Derive branch name from issue title."""
    slug = slugify(issue_title)[:30]
    timestamp = datetime.now().strftime("%y-%m-%d-%H%M")
    return f"{slug}-{timestamp}"
```

**Example:** "Add user authentication" → `add-user-authentication-25-11-29-1442`

**Problems:**

- Custom implementation of something GitHub provides natively
- Branch name derivation logic must be replicated in multiple places
- No automatic linking in GitHub UI
- Manual "Closes #N" required in PR body

### Proposed State

Use GitHub's native issue development feature:

```bash
# Creates branch with GitHub's naming convention
# Automatically links branch to issue
gh issue develop 123 --checkout
```

**GitHub's naming:** `123-add-user-authentication`

**Benefits:**

- Branch appears in issue sidebar under "Development"
- Automatic PR-to-issue linking when PR is created from branch
- No need for "Closes #N" - GitHub tracks the relationship
- Consistent with how other GitHub projects work
- Less custom code to maintain

### Implementation Notes

**Changes to `erk submit`:**

```python
# Before
branch_name = derive_branch_name_with_date(issue.title)
ctx.git.create_branch(branch_name)

# After
result = subprocess.run(
    ["gh", "issue", "develop", str(issue_number), "--checkout"],
    capture_output=True
)
branch_name = result.stdout.strip()  # GitHub returns the branch name
```

**Workflow changes:**

```yaml
# Finding the PR becomes simpler
- name: Find linked PR
  run: |
    # GitHub's native linking makes this easier
    PR_URL=$(gh issue view $ISSUE_NUMBER --json linkedBranches -q '.linkedBranches[0].pullRequest.url')
```

**Considerations:**

- Requires GitHub CLI authentication with appropriate scopes
- Branch naming is controlled by GitHub (less customizable)
- Need to handle case where branch already exists

---

## Improvement 5: Store Plan in Issue Body (Not Split)

### Current State

Plan content split across two locations:

| Location      | Content                            |
| ------------- | ---------------------------------- |
| Issue body    | `plan-header` metadata only        |
| First comment | `plan-body` with full plan content |

**Reason for split:** GitHub issue body size limits (65536 characters)

**Problems:**

- Two places to look for plan content
- Comment must be found and parsed separately
- `plan-body` stored in collapsible `<details>` adding complexity
- More API calls to reconstruct full plan

### Proposed State

Store everything in the issue body:

````markdown
# Plan: Add User Authentication

<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
created_at: 2025-01-15T10:30:00Z
created_by: username
```
````

</details>
<!-- /erk:metadata-block:plan-header -->

## Goals

1. Implement OAuth2 authentication flow
2. Add session management
3. Create login/logout UI

## Implementation Steps

1. Add OAuth2 dependencies
2. Configure authentication providers
3. Implement callback handlers
4. Create session middleware
5. Build login page component

## Context

- Using Next.js 14 app router
- PostgreSQL for session storage
- Support Google and GitHub providers

````

**Plan size limit:** If a plan exceeds ~60KB, it's probably too detailed. Encourage higher-level plans with implementation details emerging during execution.

**Benefits:**
- Single API call to get complete plan
- Simpler parsing (one location)
- Plan visible in issue body without expanding comments
- Easier for humans to read issue directly

### Implementation Notes

**Migration:** Existing issues can be migrated to body storage:

```python
def migrate_to_body_storage(issue_number: int) -> None:
    """Migrate plan from comment to issue body."""
    issue = github.get_issue(issue_number)
    plan_body = extract_plan_body(issue.comments[0])

    new_body = f"{issue.body}\n\n{plan_body}"
    github.update_issue(issue_number, body=new_body)

    # Optionally delete the plan-body comment
    delete_comment(issue.comments[0].id)
````

**Size check at creation:**

```python
def create_plan_issue(title: str, plan_content: str) -> Issue:
    """Create issue with plan content."""
    if len(plan_content) > 60_000:
        raise PlanTooLargeError(
            f"Plan is {len(plan_content)} chars. Maximum is 60,000. "
            "Consider a higher-level plan."
        )
    # ...
```

---

## Improvement 6: Let Workflow Create PR

### Current State

`erk submit` creates a draft PR locally for "correct commit attribution":

1. User runs `erk submit 123`
2. Creates branch, commits `.worker-impl/`, pushes
3. Creates draft PR via `gh pr create`
4. Dispatches workflow
5. Workflow finds existing PR and uses it

**Problems:**

- Empty/minimal commits in PR history just to create PR
- PR exists before any implementation code
- Draft PR sits empty until workflow runs
- Complexity in workflow to "find existing PR"

### Proposed State

Let the workflow create the PR after implementation:

1. User runs `erk submit 123`
2. Dispatches workflow (no branch/PR creation)
3. Workflow creates branch from issue (`gh issue develop`)
4. Workflow reconstructs `.impl/` from issue
5. Workflow runs implementation
6. Workflow creates PR with actual commits

**Workflow attribution:**

```yaml
- name: Configure git for commits
  run: |
    git config user.name "${{ inputs.submitted_by }}"
    git config user.email "${{ inputs.submitted_by }}@users.noreply.github.com"
```

**PR creation after implementation:**

```yaml
- name: Create PR with implementation
  run: |
    gh pr create \
      --title "${{ inputs.issue_title }}" \
      --body "Implementation of #${{ inputs.issue_number }}" \
      --draft
```

**Benefits:**

- Cleaner git history (no empty setup commits)
- PR contains actual implementation from the start
- Simpler `erk submit` (just dispatch, nothing else)
- No "find existing PR" logic in workflow
- PR and implementation are atomic

### Implementation Notes

**Simplified `erk submit`:**

```python
def submit(issue_number: int) -> None:
    """Submit plan for remote implementation."""
    # Validate issue
    issue = validate_issue(issue_number)

    # Dispatch workflow (that's it!)
    dispatch_workflow(
        workflow="dispatch-erk-queue-git.yml",
        inputs={
            "issue_number": issue_number,
            "submitted_by": get_current_user(),
            "issue_title": issue.title,
        }
    )

    feedback.success(f"Dispatched implementation for #{issue_number}")
```

**Workflow owns branch + PR creation:**

```yaml
jobs:
  implement:
    steps:
      - name: Create branch from issue
        run: gh issue develop ${{ inputs.issue_number }} --checkout

      - name: Reconstruct .impl from issue
        run: erk plan reconstruct --issue ${{ inputs.issue_number }}

      - name: Run implementation
        run: claude --print "/erk:plan-implement"

      - name: Create PR
        run: |
          gh pr create \
            --title "$(gh issue view ${{ inputs.issue_number }} --json title -q .title)" \
            --body "Closes #${{ inputs.issue_number }}"
```

---

## Summary of Changes

### Files to Modify

| File                                                       | Change                                                                 |
| ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| `src/erk/cli/commands/submit.py`                           | Remove branch/PR creation, `distinct_id`, simplify to dispatch-only    |
| `.github/workflows/dispatch-erk-queue-git.yml`             | Add run comment, branch creation, `.impl/` reconstruction, PR creation |
| `packages/erk-shared/src/erk_shared/worker_impl_folder.py` | Delete (no longer needed)                                              |
| `packages/erk-shared/src/erk_shared/distinct_id.py`        | Delete (no longer needed)                                              |
| `packages/erk-shared/src/erk_shared/impl_folder.py`        | Add `reconstruct_from_issue()`                                         |
| `packages/erk-shared/src/erk_shared/metadata_blocks.py`    | Consolidate to 3 block types                                           |
| `packages/erk-shared/src/erk_shared/branch_naming.py`      | Replace with `gh issue develop`                                        |

### Migration Path

1. **Phase 1:** Implement `erk plan reconstruct` command
2. **Phase 2:** Update workflow to use reconstruction instead of `.worker-impl/`
3. **Phase 3:** Replace `distinct_id` with comment-based run discovery
4. **Phase 4:** Consolidate metadata blocks (backwards-compatible parsing)
5. **Phase 5:** Switch to `gh issue develop` for branch creation
6. **Phase 6:** Move to workflow-created PRs (breaking change for in-flight plans)

### Metrics for Success

| Metric                        | Before            | After |
| ----------------------------- | ----------------- | ----- |
| Metadata block types          | 6                 | 3     |
| Folders for implementation    | 2                 | 1     |
| Custom identifier systems     | 1 (`distinct_id`) | 0     |
| Commits per implementation    | 3+                | 1-2   |
| Custom branch naming code     | ~100 lines        | 0     |
| API calls to reconstruct plan | 2                 | 1     |

---

## Related Documentation

- [Plan Lifecycle](plan-lifecycle.md) - Current lifecycle documentation
- [Planning Workflow](planning-workflow.md) - `.impl/` folder structure
- [Kit CLI Commands](kit-cli-commands.md) - Available commands

---

## Implementation Log: Improvement 4

**Status:** Complete
**Implementation Period:** Nov 30 - Dec 1, 2025
**PRs:** #1665, #1680, #1684, #1687, #1692, #1699, #1700, #1722, #1725, #1832

### What Was Implemented

Replaced custom `derive_branch_name_with_date()` with GitHub's native `gh issue develop` command across all branch-creating commands (submit, implement, wt create).

**Key Changes:**

- Branch naming changed from `my-feature-25-11-29-1430` to GitHub's native `123-my-feature` format
- Implemented `IssueDevelopment` ABC with real/fake/dry-run implementations
- Commands detect and reuse existing linked branches
- ~200 lines of custom branch naming code removed
- Eliminated `USE_GITHUB_NATIVE_BRANCH_LINKING` feature flag (always-on)
- Removed "Closes #N" keyword approach in favor of native linking

### Bugs Encountered & Fixed

1. **Tab-separated output parsing** (#1680): `gh issue develop --list` outputs `branch\tURL`, not just branch name. Fixed by splitting on tab.

2. **Branch/worktree name mismatch** (#1684): GitHub auto-generates branch names that could exceed 31 chars, breaking erk's naming invariants. Fixed by computing branch names explicitly and passing `--name` flag to `gh issue develop`.

3. **Branch name collisions** (#1699): `gh issue develop` fails when branch already exists on remote. Fixed by adding `_ensure_unique_branch_name()` that appends numeric suffixes (-1, -2, etc.).

4. **PR discovery mechanism** (#1692): Original implementation searched PR bodies for "Closes #N". Switched to using native `linkedBranches` GraphQL field for more robust discovery.

### Lessons Learned

1. **GitHub CLI output formats are not documented** - Had to discover tab-separated output through trial and error. Always test with real GitHub API, not just assumed formats.

2. **`gh issue develop` fails on existing branches** - The command also corrupts git config when it fails. Must always verify branch/link existence before invoking.

3. **Explicit is better than implicit** - Letting GitHub auto-generate branch names caused mismatches. Computing names explicitly with `--name` flag ensures predictable behavior.

4. **Native features > custom implementations** - GitHub's native branch linking provides automatic PR-to-issue linking in the UI, "Development" sidebar integration, and auto-closure on merge - all without custom code.

5. **GraphQL > REST for relationship queries** - The `linkedBranches` field provides reliable link discovery vs. searching PR bodies for keywords.

### Files Deleted (Custom Code Removed)

- `packages/erk-shared/src/erk_shared/naming.py` (partial - derive_branch_name_with_date)
- `packages/dot-agent-kit/.../get_closing_text.py`
- `packages/dot-agent-kit/.../get_pr_metadata.py`
- `src/erk/cli/constants.py` - `USE_GITHUB_NATIVE_BRANCH_LINKING` flag

### New Abstractions Added (Subsequently Removed)

> **Note**: The `gh issue develop` integration was subsequently removed in December 2025 (#2233).
> The GitHub CLI's native branch linking only provided a cosmetic UI feature (Development indicator),
> while issue closing actually works via commit message keywords ("Closes #N"). Branches are now
> created directly via git, eliminating the `gh` CLI dependency for branch operations.

- ~~`IssueDevelopment` ABC in `erk_shared/github/issue_link_branches.py`~~ (removed)
- ~~Real/Fake/DryRun implementations following existing patterns~~ (removed)
- ~~Kit CLI commands: `get-linked-branch`, `get-pr-for-branch`~~ (removed)
- ~~Documentation: `docs/agent/github-branch-linking.md`~~ (removed)
