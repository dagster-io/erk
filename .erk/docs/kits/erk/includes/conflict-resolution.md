<!-- Shared conflict resolution steps for inclusion in Claude slash commands -->
<!-- Used by: fix-conflicts.md, sync-divergence.md -->

For each conflicted file:

a. **Read the file** - Understand both sides of the conflict by examining the conflict markers:

- `<<<<<<< HEAD` marks the start of your local changes
- `=======` separates local from incoming changes
- `>>>>>>> <commit>` marks the end of incoming changes

b. **Understand intent** - Determine what each side was trying to accomplish:

- What was the local change trying to do?
- What was the remote change trying to do?
- Are they complementary or contradictory?

c. **Resolve intelligently:**

- If changes are complementary -> merge both
- If changes conflict semantically -> prefer the more recent/complete version
- If unclear -> ask the user for guidance

d. **Remove all conflict markers** - The resolved file should have no `<<<<<<<`, `=======`, or `>>>>>>>` markers

e. **Stage the resolution** - `git add <file>`
