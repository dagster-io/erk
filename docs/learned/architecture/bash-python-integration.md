---
title: Heredoc Quoting and Escaping in Agent-Generated Bash
read_when:
  - generating bash commands with heredocs in Claude Code commands or skills
  - debugging escaping issues where bash mangles content passed to git, gh, or Python
  - writing Claude Code commands that produce multi-line text via bash
tripwires:
  - action: "using unquoted heredoc delimiters (<<EOF) when the body contains $, \\, or backticks"
    warning: "Never use unquoted heredoc delimiters (<<EOF) when the body contains $, \\, or backticks \u2014 bash silently expands them"
  - action: "preferring the write tool over bash heredocs for large agent outputs"
    warning: "Prefer the Write tool over bash heredocs for large agent outputs \u2014 heredocs fail silently with special characters"
last_audited: "2026-02-07 19:35 PT"
audit_result: clean
---

# Heredoc Quoting and Escaping in Agent-Generated Bash

## Why This Matters

When Claude Code agents generate bash commands containing heredocs (for git commit messages, GitHub issue bodies, CLI arguments), the quoting mode determines whether bash interprets the content or passes it literally. The wrong choice produces **silent corruption**: bash expands `$variables`, eats backslashes, and interprets backticks without error messages.

This is cross-cutting because the pattern applies everywhere heredocs appear: commands, skills, agent-generated bash, and hooks.

## The Core Decision

**Quote the heredoc delimiter by default**: `<<'EOF'` (single-quoted) passes content literally. Unquoted `<<EOF` enables bash variable interpolation.

Most agent-generated content contains special characters that should survive literally — commit messages with `$PATH`, issue bodies with markdown code blocks containing backticks, Python regex patterns like `\s` or `\w`. Using unquoted heredocs for this content causes silent mangling.

**Why agents get this wrong:**

1. **Training data bias** — Most online examples use unquoted `<<EOF` for simple cases
2. **Silent failure mode** — Bash doesn't error; it quietly changes content
3. **Multi-layer escaping** — When heredoc body contains Python regex or shell-like syntax, each interpretation layer compounds

## The Anti-Pattern

```bash
# WRONG: Bash expands $PATH, eats \s, interprets backticks
cat <<EOF
file_path = "$PATH"
pattern = r'^\s*import'
result = `command`
EOF
```

**The fix is always `<<'EOF'` (quoted delimiter)**. If you also need variable interpolation, see hybrid patterns below.

## When You Need Both Literal Content and Variables

**Problem**: Heredoc body needs some bash variables but also contains `$` or `\` that must survive literally.

**Solution hierarchy:**

1. **Write tool** (best for agents) — Skip heredocs entirely. Guarantees exact content without escaping concerns. Mandatory pattern for agent outputs >1KB.
2. **Placeholder substitution** (preferred for bash) — Use `<<'EOF'` for literal content, post-process with `sed` to inject variables. Keeps body readable.
3. **Double escaping** (avoid) — Use `<<EOF` and double every backslash (`\\s`), escape dollar signs (`\$`). Makes body unreadable.

<!-- Source: .claude/commands/erk/learn.md, Write tool mandate for agent outputs -->

See the Write-tool-over-heredoc rationale in `.claude/commands/erk/learn.md` — agents must use the Write tool for saving agent outputs because heredocs fail silently with large content containing special characters.

## Erk Convention

<!-- Source: .claude/commands/erk/git-pr-push.md, heredoc commit pattern -->

Erk's Claude Code commands consistently use `<<'EOF'` for `gh issue create`, `gh issue comment`, `git commit -m`, and `erk exec` commands. See the commit message heredoc pattern in `.claude/commands/erk/git-pr-push.md` (uses `<<'COMMIT_MSG'` to prevent expansion).

## When to Avoid Heredocs Entirely

Prefer the Write tool over bash heredocs when:

- **Content exceeds ~1KB** — Large heredocs are fragile in agent contexts
- **Content is agent-generated** — Agent output frequently contains `$`, `\`, backticks, markdown code fences
- **Content will be read back** — Write tool creates files with exact content; heredocs add interpretation that corrupts silently

**Decision test**: If content originates from an agent (TaskOutput, subagent results, AI-generated text), use the Write tool. Heredocs are for human-authored content in command/skill files.
