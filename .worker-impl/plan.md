# Plan: Create User-Facing Configuration Documentation

## Summary

Create comprehensive user documentation for all erk config flags at `docs/user/config.md` and document the docs folder audience convention in AGENTS.md.

## Files to Modify

1. **Create**: `docs/user/config.md` - New config reference documentation
2. **Modify**: `docs/user/README.md` - Add link to new config doc
3. **Modify**: `AGENTS.md` - Add docs folder audience convention

## Implementation

### 1. Create `docs/user/config.md`

Document all config options with:
- Option name and type
- Default value
- What it does
- When/why to change it
- Example usage

**Global Config Options** (stored in `~/.erk/config.toml`):

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `erk_root` | Path | Set at init | Root directory for erk metadata |
| `use_graphite` | Boolean | Auto-detected | Enable Graphite integration |
| `show_pr_info` | Boolean | true | Show PR info in worktree listings |
| `github_planning` | Boolean | true | GitHub planning integration |
| `auto_restack_skip_dangerous` | Boolean | false | Skip --dangerous flag for auto-restack |
| `shell_setup_complete` | Boolean | false | Internal: shell integration status |

**Repo Config Options** (stored in `.erk/config.toml`):
- `trunk-branch` - The trunk branch name

**Project Config Options** (stored in `.erk/project.toml`):
- `env` - Environment variables
- `post_create.shell` - Shell for post-create commands
- `post_create.commands` - Commands to run after worktree creation

### 2. Update `docs/user/README.md`

Add entry for config.md:
```markdown
- [Configuration Reference](config.md) - All config options and their usage
```

### 3. Update `AGENTS.md`

Add under "Project Naming Conventions" or create new "Documentation Structure" section:

```markdown
**Documentation Structure:** The `docs/` folder uses subfolders named for the intended audience:
- `docs/user/` - End-user documentation (how to use erk)
- `docs/developer/` - Developer documentation (contributing to erk)
- `.erk/docs/agent/` - Agent documentation (AI/Claude instructions)
```

## Related Documentation

- Skills: None needed (documentation only)
- Docs: None needed