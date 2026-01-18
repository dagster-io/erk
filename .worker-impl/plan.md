# Learn Plan: Document Auto-Execution Pattern

## Context

During implementation of plan #5192 (Post-Init Prompt Hook), we discovered the "auto-execution pattern" - a technique where CLI commands output instructions that Claude automatically follows within the same session, without requiring a separate slash command.

**Original approach (rejected):** Create `/erk:post-init` slash command that users manually invoke after `erk init`

**Final approach (accepted):** Have `erk init` output an instruction like "Now read and execute .erk/prompt-hooks/post-init.md" which Claude directly follows

## Insight

CLI commands can communicate with Claude by outputting action instructions in their output. Claude reads this output and executes the requested action within the same session. This eliminates the need for:
- Manual user intervention to run a follow-up command
- Creating slash commands for automated follow-up actions
- Multi-step workflows where users must remember to run additional commands

## Documentation Plan

### File to Create
`docs/learned/cli/auto-execution-pattern.md`

### Content Structure

1. **Overview**: Explain what the auto-execution pattern is
2. **When to Use**: Guidance on when this pattern is appropriate vs slash commands
3. **Implementation Pattern**: Code examples showing how to output instructions Claude will follow
4. **Examples in Codebase**: Reference `erk init` post-init hook detection
5. **Anti-patterns**: When NOT to use this (e.g., destructive actions, user-choice situations)

### Key Points to Document

- CLI output is visible to Claude and can contain actionable instructions
- Instructions should be clear and specific (e.g., "Now read and execute X" not "consider running X")
- This pattern works because Claude processes the full session context including command output
- Contrast with slash commands (explicit user invocation) vs auto-execution (implicit continuation)

## Related Documentation

- Update `docs/learned/index.md` to include the new document
- Consider cross-reference from `docs/learned/hooks/prompt-hooks.md`

## Validation

- Document should be clear enough that an agent implementing a similar feature would choose auto-execution over slash command when appropriate