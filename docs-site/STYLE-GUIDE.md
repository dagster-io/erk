# Erk Documentation Style Guide

Style conventions for writing erk documentation. Adapted from internal engineering docs standards.

## Voice and tone

- **Direct and concise.** Say what you mean in as few words as possible.
- **Second person.** Address the reader as "you."
- **Active voice.** "Erk creates a worktree" not "A worktree is created by erk."
- **Present tense.** "The command runs" not "The command will run."
- **Confident, not hedging.** "This works because" not "This should work because."

## Banned words and phrases

| Avoid                   | Use instead         |
| ----------------------- | ------------------- |
| simply, just, easy      | _(drop the word)_   |
| leverage                | use                 |
| utilize                 | use                 |
| in order to             | to                  |
| it should be noted that | _(drop the phrase)_ |
| please                  | _(drop the word)_   |
| basically               | _(drop the word)_   |
| obviously, clearly      | _(drop the word)_   |

## Terminology

Use these terms consistently:

| Term          | Usage                                                                      |
| ------------- | -------------------------------------------------------------------------- |
| plan          | A structured implementation document (not "ticket" or "task")              |
| worktree      | A git worktree for isolated development (not "workspace" or "branch copy") |
| stack         | A sequence of dependent PRs managed by Graphite                            |
| implement     | Execute a plan to produce code (not "build" or "develop")                  |
| dispatch      | Send a plan for remote autonomous execution                                |
| land          | Merge a PR (not "ship" or "deploy")                                        |
| root worktree | The primary git worktree (not "main worktree")                             |

## Section litmus tests

Before publishing a section, verify:

- **Getting Started**: Can a new user follow this without prior erk knowledge?
- **Concepts**: Does this explain _why_, not just _how_?
- **Guides**: Does this walk through a complete workflow with concrete steps?
- **Reference**: Is every parameter and option documented?

## Formatting conventions

- Use **bold** for UI elements and key terms on first use
- Use `code` for commands, file paths, and code references
- Use fenced code blocks with language tags for examples
- Use admonitions (:::note, :::tip, :::caution) sparingly
- Keep paragraphs to 3-4 sentences maximum
- Use numbered lists for sequential steps, bullet lists for unordered items

## File naming

- Prefix files with a two-digit number for sidebar ordering: `01-introduction.md`
- Use lowercase kebab-case: `plan-oriented-engineering.md`
- Match the title to the filename where possible

## Code examples

- Show the command first, then explain what it does
- Use realistic values, not `foo`/`bar` placeholders
- Include expected output when it helps understanding
- Keep examples minimal — show one concept per block
