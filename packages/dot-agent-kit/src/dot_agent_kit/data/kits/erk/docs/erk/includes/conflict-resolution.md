## Conflict Resolution Process

### Build Context

- Run `git log --since="1 week ago" --oneline` to see recent commits
- Use `git show` on relevant commits to understand the purpose of conflicting changes
- Build a mental model of why these conflicts are occurring

### Analyze Each Conflicted File

Read the file to understand the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).

Determine what changes are in HEAD vs the incoming commit.

### Classify the Conflict

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

For mechanical conflicts: **Auto-resolve** by:

- Intelligently merging both changes when they're independent
- Choosing the more recent/complete version when one supersedes the other
- Preserving the intent of both changes where possible

### Clean Up

Remove all conflict markers after resolution.
