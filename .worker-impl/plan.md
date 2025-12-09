# Extraction Plan: AllUsers Sentinel Pattern Documentation

## Objective

Update existing sentinel pattern documentation to include the new `AllUsers` sentinel pattern for filter parameters, extending the existing `PRNotFound` pattern documentation.

## Source Information

- **Plan Session**: 37f6023a-22c2-4a69-96e4-9ea43a29d07b (from issue #2888)
- **Implementation Session**: a36e89f4-f36a-4866-ad7e-a8877dff4ab1

## Documentation Items

### Item 1: Update Not-Found Sentinel Pattern Documentation

**Type**: Category B (Teaching Gap) - Documentation for what was BUILT
**Location**: `docs/agent/architecture/not-found-sentinel.md`
**Action**: Update existing document to include filter sentinels
**Priority**: High - Extends an existing, well-used pattern document

**Rationale**: The existing `not-found-sentinel.md` documents `PRNotFound` for lookup operations. The new `AllUsers` sentinel follows the same philosophy (sentinel instead of None) but for a different use case: filter parameters where `None` could be accidentally passed. This belongs in the same document as a second section.

**Draft Content to Add**:

```markdown
## Filter Sentinel Pattern

A related pattern uses sentinels for filter parameters where `None` could be dangerously interpreted as "all" or "no filter":

### The Problem

```python
# DANGEROUS: None means "all users" - but what if auth fails?
def list_issues(creator: str | None = None):
    if creator is None:
        return all_issues  # Oops - auth failure shows everyone's data!
```

### The Solution

```python
@dataclass(frozen=True)
class AllUsers:
    """Sentinel indicating explicit 'all users' filter.

    Use this instead of None to make the 'no filter' intention explicit,
    preventing accidental data exposure from auth failures or forgotten parameters.
    """
    pass

# Singleton instance
ALL_USERS = AllUsers()

# Type alias for cleaner signatures
CreatorFilter = str | AllUsers

def list_issues(creator: CreatorFilter) -> list[Issue]:
    """List issues, optionally filtered by creator.

    Args:
        creator: Username to filter by, or ALL_USERS for no filter
    """
    if isinstance(creator, AllUsers):
        return all_issues
    return [i for i in all_issues if i.author == creator]
```

### Why Sentinel Instead of None for Filters?

| Scenario | `None` Behavior | Sentinel Behavior |
|----------|----------------|-------------------|
| Auth fails, returns `None` | Shows ALL data (dangerous!) | Type error - must explicitly pass `ALL_USERS` |
| Developer forgets to set param | Shows ALL data (default) | Must explicitly choose |
| Intentional "all users" | Works but indistinguishable | `ALL_USERS` is explicit |

### When to Use Filter Sentinels

**Use filter sentinels when:**
- `None` could be passed accidentally (auth failures, unset variables)
- The "no filter" case exposes sensitive data
- You want callers to explicitly opt into broad queries

**Use `None` when:**
- The filter is non-sensitive (e.g., date ranges)
- Accidental `None` has no security implications
- The API is internal and controlled

### Example: AllUsers in erk

```python
from erk_shared.github.types import AllUsers, ALL_USERS, CreatorFilter

# In GitHub ABC
def get_issues_with_pr_linkages(
    self,
    location: GitHubRepoLocation,
    labels: list[str],
    creator: CreatorFilter,  # Must be explicit
) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
    ...

# Usage - must explicitly choose
issues = github.get_issues_with_pr_linkages(
    location,
    labels=["erk-plan"],
    creator=ALL_USERS,  # Explicit: I want all users
)

# Or filter to current user
issues = github.get_issues_with_pr_linkages(
    location,
    labels=["erk-plan"],
    creator=current_user,  # Only my issues
)
```
```

### Item 2: Update Tripwire for Filter Sentinels

**Type**: Category A (Learning Gap) - Would help future sessions
**Location**: `docs/agent/tripwires.md` (generated from frontmatter)
**Action**: Add tripwire to `not-found-sentinel.md` frontmatter
**Priority**: Medium - Prevents repeating the "None for all" anti-pattern

**Draft Frontmatter Addition** (to `not-found-sentinel.md`):

```yaml
tripwires:
  - action: "checking if get_pr_for_branch() returned a PR"
    warning: "Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None."
  - action: "using None to mean 'all' or 'no filter' in a parameter"
    warning: "Consider using a sentinel like AllUsers instead. None could be passed accidentally from auth failures or unset variables."
```

### Item 3: Add read_when Condition

**Type**: Category A (Learning Gap)
**Location**: `docs/agent/architecture/not-found-sentinel.md` frontmatter
**Action**: Add read_when for filter sentinel use case
**Priority**: Low - Helps discoverability

**Draft Frontmatter Addition**:

```yaml
read_when:
  - "designing return types for lookup operations"
  - "handling missing resource cases without exceptions"
  - "checking if get_pr_for_branch() returned a PR"
  - "working with GitHub PR lookup results"
  - "using None to represent 'all' or 'no filter' in parameters"  # NEW
  - "designing filter parameters that could expose sensitive data"  # NEW
```

## Files to Modify

1. `docs/agent/architecture/not-found-sentinel.md` - Add filter sentinel section, update frontmatter

## Implementation Steps

1. Read current `not-found-sentinel.md`
2. Add "Filter Sentinel Pattern" section after existing content
3. Update frontmatter with new tripwire and read_when conditions
4. Run `erk docs sync` to regenerate `tripwires.md` and `index.md`
5. Verify changes with `erk docs check`