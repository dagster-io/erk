# Plan Storage Location

**Plan file location:**

- Directory: `~/.claude/plans/`
- Format: `{slug}.md` files
- Example: `~/.claude/plans/add-user-authentication.md`

**Plan extraction:**

- Reads `.md` files from `~/.claude/plans/`
- Returns the most recently modified plan file
- No parsing required - plans are stored as plain markdown
