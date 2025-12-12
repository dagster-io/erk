## Conflict Resolution Process

### Build Context

- Run `git log --since="1 week ago" --oneline` to see recent commits
- Use `git show` on relevant commits to understand the purpose of conflicting changes
- Build a mental model of why these conflicts are occurring

### Analyze Each Conflicted File

Read the file to understand the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).

Determine what changes are in HEAD vs the incoming commit.

### Classify the Conflict

Use this decision tree to classify conflicts:

```
Is the change about HOW to do something?
├── YES: Different algorithms/approaches?
│   ├── YES → SEMANTIC (ask user)
│   └── NO: Just different implementations of same approach?
│       └── Merge both if compatible, otherwise SEMANTIC
└── NO: Is it about code structure?
    ├── Imports/formatting/ordering → MECHANICAL
    ├── Type annotations → MECHANICAL
    └── Independent additions to same location → MECHANICAL
```

**Semantic/Purpose Conflicts** - When changes have conflicting intent:

- Two different approaches to solving the same problem
- Architectural disagreements
- Contradictory business logic

For semantic conflicts: **STOP and alert the user** with:

- A clear explanation of the conflicting purposes
- The reasoning behind each approach based on commit history
- Ask the user which approach to take

**Mechanical Conflicts** - When conflicts are purely mechanical:

- Adjacent line changes
- Import reordering
- Formatting differences
- Independent features touching the same file
- Type annotation updates

For mechanical conflicts: **Auto-resolve** by:

- Intelligently merging both changes when they're independent
- Choosing the more recent/complete version when one supersedes the other
- Preserving the intent of both changes where possible

### Real-World Examples

#### Example 1: Tuple Type Annotation Merge (Mechanical)

**File:** `packages/erk-shared/src/erk_shared/graphite/fake.py`

**Conflict:**

```python
<<<<<<< HEAD
        branch: str,
        parent: str,
        has_pr: bool,
        pr_number: int | None,
=======
        branch: str,
        parent: str,
        has_pr: bool,
>>>>>>> incoming
```

**Analysis:** HEAD added `pr_number` field to tuple. Incoming doesn't have it. These are independent additions - HEAD is more complete.

**Resolution:** Keep HEAD version (includes all fields).

#### Example 2: Constructor Parameter Updates (Mechanical)

**File:** `packages/erk-shared/src/erk_shared/git/fake.py`

**Conflict:**

```python
<<<<<<< HEAD
class FakeGit(Git):
    def __init__(
        self,
        current_branch: str = "main",
        branches: dict[str, str] | None = None,
        worktrees: list[tuple[str, str, str, bool]] | None = None,
        rebase_in_progress: bool = False,
        conflicted_files: list[str] | None = None,
    ) -> None:
=======
class FakeGit(Git):
    def __init__(
        self,
        current_branch: str = "main",
        branches: dict[str, str] | None = None,
        worktrees: list[tuple[str, str, str]] | None = None,
    ) -> None:
>>>>>>> incoming
```

**Analysis:** HEAD has more parameters for testing rebase scenarios. Incoming has simpler version. Independent feature additions.

**Resolution:** Keep HEAD version (superset of functionality).

#### Example 3: Import Reordering (Mechanical)

**File:** `src/erk/cli/commands/pr/submit_cmd.py`

**Conflict:**

```python
<<<<<<< HEAD
from erk_shared.integrations.gt.types import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
    RestackPreflightSuccess,
)
=======
from erk_shared.integrations.gt.types import (
    PostAnalysisError,
    PostAnalysisResult,
    PreAnalysisError,
    PreAnalysisResult,
)
>>>>>>> incoming
```

**Analysis:** HEAD imports additional type for restack feature. Incoming doesn't need it. Pure additive change.

**Resolution:** Keep HEAD version (includes new import).

#### Example 4: Semantic Conflict (Requires User)

**File:** `src/erk/core/retry.py`

**Conflict:**

```python
<<<<<<< HEAD
def retry_with_backoff(func, max_attempts=3):
    """Exponential backoff: 1s, 2s, 4s..."""
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception:
            delay = 2 ** attempt
            time.sleep(delay)
=======
def retry_with_backoff(func, max_attempts=3):
    """Fixed delay: always 2s between attempts."""
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception:
            time.sleep(2)
>>>>>>> incoming
```

**Analysis:** HEAD uses exponential backoff (1s, 2s, 4s). Incoming uses fixed 2s delay. These are fundamentally different approaches with different trade-offs.

**Resolution:** **STOP - Ask user:**

- Exponential backoff: Better for rate-limited APIs, but slower recovery
- Fixed delay: Predictable timing, faster recovery, but may hit rate limits

### Clean Up

Remove all conflict markers after resolution.

Ensure the resolved code:

1. Compiles/parses correctly
2. Has consistent style with surrounding code
3. Includes all necessary imports for new code
4. Maintains type correctness
