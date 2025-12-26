## <!-- Based originally on https://motlin.com/blog/claude-code-utility-commands -->

🔀 Fix all merge conflicts and continue the git rebase.

- Check `git status` to understand the state of the rebase and identify conflicted files
- Analyze recent commit history (past week) to understand the context of the changes:
  - Run `git log --since="1 week ago" --oneline` to see recent commits
  - Use `git show` on relevant commits to understand the purpose of conflicting changes
  - Build a mental model of why these conflicts are occurring
- For each conflicted file:
  - Read the file to understand the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
  - Analyze what changes are in HEAD vs the incoming commit
  - Determine the nature of the conflict:
    - **Semantic/Purpose conflicts**: If the changes have conflicting intent or purpose (e.g., two different approaches to solving the same problem, architectural disagreements, or contradictory business logic), STOP and alert the user with:
      - A clear explanation of the conflicting purposes
      - The reasoning behind each approach based on commit history
      - Ask the user which approach to take
    - **Mechanical conflicts**: If the conflicts are purely mechanical (e.g., adjacent line changes, import reordering, formatting differences, or independent features touching the same file), automatically resolve by:
      - Intelligently merging both changes when they're independent
      - Choosing the more recent/complete version when one supersedes the other
      - Preserving the intent of both changes where possible
  - Remove all conflict markers after resolution
- ✅ After resolving all conflicts:
  - If project memory includes a precommit check then run it and ensure no failures
  - Stage the resolved files with `git add`
  - Continue the rebase with `gt continue`
- If the rebase continues with more conflicts, repeat the process
- ✔️ Verify successful completion by checking git status and recent commit history
