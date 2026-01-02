# Conflict Resolution Logic

For each file in the conflicts list, classify and resolve:

## 1. Read the conflict markers

```bash
git show :1:path/to/file > base.tmp
git show :2:path/to/file > ours.tmp
git show :3:path/to/file > theirs.tmp
```

## 2. Classify the conflict

**Mechanical conflicts** (auto-resolve):

- Adjacent line changes that don't overlap
- Import reordering (both sides add different imports)
- Formatting differences (whitespace, line breaks)
- Independent features touching the same file region
- Tuple type annotation changes (e.g., `tuple[str]` vs `tuple[str, ...]`)

**Semantic conflicts** (require user decision):

- Different approaches to the same problem
- Contradictory business logic
- Incompatible API changes
- Architectural disagreements

## 3. Resolve mechanical conflicts

For mechanical conflicts, read the file and determine the resolution:

- If changes are on adjacent lines → Accept both changes
- If one side is a superset → Use the superset
- If changes are independent → Merge both changes
- If formatting only → Use incoming formatting

Write the resolved content back to the file.

## 4. For semantic conflicts

If the conflict is semantic, present the options to the user:

```
🤔 Semantic conflict in <file>:
   HEAD: <description of current approach>
   INCOMING: <description of incoming approach>

   Which approach should be used?
   1. Keep HEAD (<current approach>)
   2. Keep INCOMING (<incoming approach>)
   3. Combine both approaches
```

Wait for user input and apply their choice.

## 5. Verify resolution

After resolving each file:

- Ensure no conflict markers remain (`<<<<<<<`, `=======`, `>>>>>>>`)
- If the project has a linter/formatter in memory, run it to verify syntax
- Report if the resolution introduced issues
