---
title: Heredoc Quoting and Escaping in Agent-Generated Bash
read_when:
  - generating bash commands with heredocs in Claude Code commands or skills
  - debugging escaping issues where bash mangles content passed to git, gh, or Python
  - writing Claude Code commands that produce multi-line text via bash
tripwires:
  - Never use unquoted heredoc delimiters (<<EOF) when the body contains $, \, or backticks — bash silently expands them
  - Prefer the Write tool over bash heredocs for large agent outputs — heredocs fail silently with special characters
last_audited: "2026-02-07 18:44 PT"
audit_result: clean
---

# Heredoc Quoting and Escaping in Agent-Generated Bash

## Why This Matters

Erk's Claude Code commands and skills frequently generate bash commands containing heredocs — for git commit messages, GitHub issue bodies, and CLI arguments. The quoting mode of the heredoc delimiter determines whether bash interprets the content or passes it literally. Getting this wrong produces **silent corruption**: bash expands `$variables`, eats backslashes, and interprets backticks without any error message.

This is a cross-cutting concern because the same escaping rules apply everywhere heredocs appear: `.claude/commands/`, `.claude/skills/`, agent-generated bash, and hook scripts.

## The Core Decision: Quoted vs Unquoted Delimiter

| Heredoc Style | Bash Behavior | Use When |
| --- | --- | --- |
| `<<EOF` | Expands `$var`, `\n`, backticks | You need bash variable interpolation in the body |
| `<<'EOF'` | Literal pass-through, no expansion | Body contains `$`, `\`, backticks, or regex patterns |

**Default to `<<'EOF'`** (single-quoted). The unquoted form is an opt-in for interpolation, not the default. This is the opposite of most developers' muscle memory, which is why agents keep getting it wrong.

## Why Agents Get This Wrong

1. **Training data bias** — Most heredoc examples online use unquoted `<<EOF` because humans write simple cases
2. **Silent failure mode** — Bash doesn't error on expansion; it quietly changes the content
3. **Multi-layer escaping** — When heredoc body contains Python regex (`\s`, `\w`) or shell-like syntax (`$PATH`), each layer of interpretation compounds

## Anti-Pattern: Unquoted Heredoc with Special Characters

```bash
# WRONG: Bash expands $PATH, eats \s, interprets backticks
cat <<EOF
file_path = "$PATH"
pattern = r'^\s*import'
result = `command`
EOF
```

The fix is always the same: quote the delimiter (`<<'EOF'`). If you also need variable interpolation, see the hybrid pattern below.

## Hybrid Pattern: When You Need Both Literal Content and Variables

**Problem**: The heredoc body needs some bash variables but also contains `$` or `\` characters that must survive literally.

**Approach 1 — Double escaping** (avoid when possible): Use `<<EOF` and double every backslash (`\\s`), escape dollar signs (`\$`). This makes the body unreadable.

**Approach 2 — Placeholder substitution** (preferred): Use `<<'EOF'` for literal content, then post-process with `sed` to inject variables. This keeps the body clean and readable.

**Approach 3 — Use the Write tool** (best for agents): Skip bash heredocs entirely. The Write tool guarantees exact content without escaping concerns. This is why the `/erk:learn` command mandates the Write tool over heredocs for agent outputs.

## Erk-Specific Patterns

Erk's Claude Code commands use `<<'EOF'` consistently for `gh issue create`, `gh issue comment`, `git commit -m`, and `erk exec` commands. This is a deliberate convention.

<!-- Source: .claude/commands/erk/git-pr-push.md, heredoc commit pattern -->

See the commit message heredoc pattern in `.claude/commands/erk/git-pr-push.md` — it uses `<<'COMMIT_MSG'` to prevent expansion of commit message content.

<!-- Source: .claude/commands/erk/learn.md, Write tool vs heredoc rationale -->

See the Write-tool-over-heredoc rationale in `.claude/commands/erk/learn.md` — heredocs fail silently with large agent outputs containing special characters.

## When to Avoid Heredocs Entirely

Prefer the Write tool over bash heredocs when:

- **Content exceeds ~1KB** — Large heredocs are fragile in agent contexts
- **Content is agent-generated** — Agent output frequently contains `$`, `\`, backticks, and markdown code fences that interact badly with bash interpretation
- **Content will be read back** — The Write tool creates the file with exact content; heredocs add an interpretation layer that can corrupt silently
