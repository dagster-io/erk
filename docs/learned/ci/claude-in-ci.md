---
title: Running Claude Code in GitHub Actions
read_when:
  - Setting up Claude Code in CI workflows
  - Using claude --print in GitHub Actions
  - Automating tasks with Claude in CI
---

# Running Claude Code in GitHub Actions

## Installation

```yaml
- name: Install Claude Code
  run: |
    curl -fsSL https://claude.ai/install.sh | bash
    echo "$HOME/.claude/local/bin" >> $GITHUB_PATH
```

## Required Flags for CI

When running Claude in CI with `--print` mode, use these flags:

```yaml
- name: Run Claude
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    claude --print \
      --model claude-sonnet-4-20250514 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      --verbose \
      < .claude/commands/your-command.md
```

### Flag Reference

| Flag                             | Purpose                                   |
| -------------------------------- | ----------------------------------------- |
| `--print`                        | Non-interactive mode, outputs to stdout   |
| `--model`                        | Specify model (sonnet, opus, etc.)        |
| `--output-format stream-json`    | Stream JSON output for CI logging         |
| `--dangerously-skip-permissions` | Skip permission prompts (required for CI) |
| `--verbose`                      | Detailed logging                          |
| `--allowedTools`                 | Restrict available tools (optional)       |

## Authentication

Use either:

- `ANTHROPIC_API_KEY` - Direct API key
- `CLAUDE_CODE_OAUTH_TOKEN` - OAuth token (preferred for org accounts)

```yaml
env:
  CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
  ANTHROPIC_API_KEY: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN == '' && secrets.ANTHROPIC_API_KEY || '' }}
```

## Invoking Commands

Use stdin redirection to pass command file content:

```yaml
claude --print ... < .claude/commands/ci/autofix.md
```

Commands should be markdown files in `.claude/commands/` directory. The file content becomes the prompt.

**Note**: Slash command syntax (`"/ci:autofix"`) does NOT work in `--print` mode. Always use stdin redirection.

## Restricting Tools

Use `--allowedTools` to limit what Claude can do:

```yaml
--allowedTools 'Read(*),Bash(uv run:*),Bash(prettier:*),Bash(make:*),Bash(git:*)'
```

Pattern format: `ToolName(pattern)` where pattern uses glob syntax.

## Git Configuration

If Claude needs to commit, configure git identity first:

```yaml
- name: Configure git
  run: |
    git config user.name "erk-bot"
    git config user.email "erk-bot@users.noreply.github.com"
```

## Complete Example

```yaml
jobs:
  autofix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}
          fetch-depth: 0

      - name: Install Claude Code
        run: |
          curl -fsSL https://claude.ai/install.sh | bash
          echo "$HOME/.claude/local/bin" >> $GITHUB_PATH

      - name: Configure git
        run: |
          git config user.name "erk-bot"
          git config user.email "erk-bot@users.noreply.github.com"

      - name: Run Claude
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          claude --print \
            --model claude-sonnet-4-20250514 \
            --output-format stream-json \
            --dangerously-skip-permissions \
            --verbose \
            < .claude/commands/ci/autofix.md
```

## Common Mistakes

1. **Missing `--output-format stream-json`** - CI logs won't show streaming output
2. **Missing `--dangerously-skip-permissions`** - Claude will hang waiting for permission
3. **Using slash command syntax** - `"/ci:autofix"` doesn't work in `--print` mode; use stdin redirection
4. **Forgetting `$GITHUB_PATH`** - Claude binary won't be in PATH for subsequent steps
