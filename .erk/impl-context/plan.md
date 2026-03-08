# Plan: Create Agent-Friendly CLI Principles Document

## Context

We just completed extensive research for Objective #9009 (Agent-Friendly CLI) — analyzing Justin Poehnelt's article, the Google Workspace CLI, and erk's current state. This research should be captured as a learned doc so future sessions don't need to reconstruct it.

## What to Create

New file: `docs/learned/cli/agent-friendly-cli.md`

A principles document capturing:
1. The core patterns for making CLIs agent-friendly (from article + gws analysis)
2. Which patterns erk adopts and why
3. Which patterns erk skips and why
4. The `--json` output contract and decorator pattern
5. The structured error contract
6. The schema introspection approach
7. Reference to Objective #9009

## Verification

- `erk docs sync` passes
- Doc appears in `docs/learned/cli/index.md` after sync
- Tripwires are valid structured format
