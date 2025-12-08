---
title: Issue Reference Flow
read_when:
  - "issue references are not appearing in PRs"
  - "debugging 'Closes #N' functionality"
  - "understanding how issue.json is created and consumed"
  - "implementing commands that need issue context"
---

# Issue Reference Flow

Issue references flow through the erk system via `issue.json` files stored in implementation directories. This document describes how references are created, stored, and consumed.

## Data Structure

**File:** `.impl/issue.json` or `.worker-impl/issue.json`

**Format:**

```json
{
  "issue_number": 2670,
  "issue_url": "https://github.com/owner/repo/issues/2670"
}
```

**Python representation:** `IssueReference` dataclass in `erk_shared/impl_folder.py`

```python
@dataclass
class IssueReference:
    issue_number: int
    issue_url: str
```

## Creation

Issue references are created by:

### 1. create_worker_impl_folder()

**Location:** `erk_shared/impl_folder.py`

**Used when:** Creating `.worker-impl/` for remote implementation

**Code:**

```python
save_issue_reference(impl_dir, issue_number, issue_url)
```

### 2. erk wt create --from-issue

**Location:** CLI command for creating worktrees from issues

**Used when:** Creating local worktree with implementation folder

**Code:**

```python
save_issue_reference(impl_dir, issue_number, issue_url)
```

### 3. save_issue_reference()

**Location:** `erk_shared/impl_folder.py`

**Function:**

```python
def save_issue_reference(impl_dir: Path, issue_number: int, issue_url: str) -> None:
    """Save issue reference to issue.json in implementation directory."""
    issue_file = impl_dir / "issue.json"
    issue_data = {
        "issue_number": issue_number,
        "issue_url": issue_url
    }
    issue_file.write_text(json.dumps(issue_data, indent=2))
```

## Reading

Issue references are read by:

### 1. has_issue_reference()

**Location:** `erk_shared/impl_folder.py`

**Purpose:** Check if issue reference exists

**Function:**

```python
def has_issue_reference(impl_dir: Path) -> bool:
    """Check if implementation directory has issue reference."""
    issue_file = impl_dir / "issue.json"
    return issue_file.exists()
```

### 2. read_issue_reference()

**Location:** `erk_shared/impl_folder.py`

**Purpose:** Read issue reference from file

**Function:**

```python
def read_issue_reference(impl_dir: Path) -> IssueReference:
    """Read issue reference from issue.json in implementation directory."""
    issue_file = impl_dir / "issue.json"
    data = json.loads(issue_file.read_text())
    return IssueReference(
        issue_number=data["issue_number"],
        issue_url=data["issue_url"]
    )
```

## Consumers

Commands and tools that read from `.impl/issue.json`:

### 1. finalize.py (Local PR Submission)

**Location:** `erk_shared/finalize.py`

**Behavior:**

- Checks `has_issue_reference(impl_dir)` ✅
- If true, reads reference and adds `Closes #N` to PR body ✅
- Works correctly for local Graphite submissions ✅

### 2. get-pr-body-footer (Remote PR Submission)

**Location:** Kit CLI command

**Expected behavior:**

- Should check `has_issue_reference(impl_dir)`
- Should read reference and include `Closes #N` in footer
- Should NOT require explicit `--issue-number` parameter when `.impl/issue.json` exists

**Current behavior:** May require explicit parameters (needs verification)

### 3. Implementation Agents

**Location:** Various agent workflows

**Behavior:**

- Read issue context for understanding implementation scope
- Include issue reference in commit messages or PR descriptions
- Link back to original issue for traceability

## Anti-Pattern: Explicit Parameters

**MUST NOT:** Require `--issue-number` when `.impl/issue.json` exists

**Why:** Breaks the principle of automatic context discovery

**Wrong:**

```bash
# Requires manual parameter even though issue.json exists
dot-agent run erk get-pr-body-footer --issue-number 2670
```

**Correct:**

```bash
# Auto-reads from .impl/issue.json if present
dot-agent run erk get-pr-body-footer
```

## Lifecycle

1. **Creation:** Issue reference saved to `issue.json` when implementation folder is created
2. **Copy:** In remote workflows, `.worker-impl/issue.json` is copied to `.impl/issue.json`
3. **Reading:** Commands auto-read from `.impl/issue.json` during implementation
4. **Consumption:** PR body includes `Closes #N` from issue reference
5. **Cleanup:** `.worker-impl/` deleted after success, `.impl/` left for user review

## Common Pitfalls

### Missing 'Closes #N' in Remote PRs

**Symptom:** Local PRs have `Closes #N`, but remote PRs don't

**Root cause:** Remote commands not calling `has_issue_reference()` and `read_issue_reference()`

**Fix:** Update remote PR body generation to auto-read from `.impl/issue.json`

### Requiring Explicit Parameters

**Symptom:** Commands require `--issue-number` even when `issue.json` exists

**Root cause:** Commands not implementing auto-discovery pattern

**Fix:** Add fallback logic:

```python
if not issue_number and has_issue_reference(impl_dir):
    ref = read_issue_reference(impl_dir)
    issue_number = ref.issue_number
```

## Related Documentation

- [PR Finalization Paths](pr-finalization-paths.md) - How issue references flow to PR bodies
- [Implementation Folder Lifecycle](impl-folder-lifecycle.md) - Understanding `.impl/` vs `.worker-impl/`
