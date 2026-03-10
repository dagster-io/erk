# Update Root README to Reference Dagster OSS

## Context

The erk root `README.md` is a self-contained introduction to erk that covers installation, the core workflow, and links to documentation. However, it doesn't mention that erk is actively used in the [dagster OSS repository](https://github.com/dagster-io/dagster) — the primary real-world showcase of erk in production.

The dagster OSS repo has a full erk integration including:
- `.erk/config.toml` — repository configuration
- `.erk/prompt-hooks/` — AI workflow customization
- `.claude/commands/erk/` — 17+ erk slash commands
- `.claude/agents/` — custom AI agents

Referencing dagster OSS from the README gives new users a concrete example of how erk looks in a real, large-scale codebase. This is valuable because erk's documentation and tutorials use a toy starter project, but seeing the full integration in a production repo provides much deeper understanding.

## Changes

### File: `README.md` (modify)

Add a new section after the "Documentation" table (at the end of the file) called "Real-World Example" that points to the dagster OSS repository as a showcase of erk in production use.

The section should include:
- A link to `https://github.com/dagster-io/dagster` as the primary real-world example
- A brief description noting it's an open-source data pipeline orchestrator that uses erk for plan-oriented agentic engineering
- Bullet points highlighting the key erk integration points users can explore:
  - `.erk/` directory for repository configuration and prompt hooks
  - `.claude/commands/erk/` for erk slash commands
  - `CLAUDE.md` for agent instructions that reference erk workflows

The tone should match the existing README: concise, practical, no hype. It should not duplicate what's already in `docs/TAO.md` about Dagster Labs being the origin — this section is about showing users where to look for a real example, not explaining the organizational relationship.

### Example content (adapt as needed)

```markdown
## Real-World Example

The [dagster](https://github.com/dagster-io/dagster) repository uses erk for its development workflow. Explore it to see how erk integrates with a large-scale open source codebase:

- **`.erk/`** — Repository configuration and prompt hooks
- **`.claude/commands/erk/`** — Erk slash commands for the development team
- **`CLAUDE.md`** — Agent instructions referencing erk workflows
```

## Files NOT Changing

- `docs/TAO.md` — Already references Dagster Labs; no changes needed
- `AGENTS.md` / `CLAUDE.md` — Agent instructions, not user-facing README
- `docs/` subdirectories — The documentation site has its own structure; this plan only affects the root README
- `CHANGELOG.md` — Never modified directly per project constraints

## Implementation Details

- This is a single-file, content-only change (no code, no tests)
- Place the new section at the end of the file, after the Documentation table
- Use the same markdown formatting style as the existing README (headers, bullet points, inline code for paths)
- Link to the dagster repo's default branch (no specific commit or tag)

## Verification

1. Read `README.md` after the edit and confirm:
   - The new section appears after the Documentation table
   - All links are valid GitHub URLs
   - Formatting is consistent with the rest of the file
   - No existing content was removed or modified
2. Confirm no other files were changed
