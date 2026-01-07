# Prerequisites

Before installing erk, ensure you have the following tools installed. Each tool is essential for the erk workflow.

## Required Tools

### Python 3.10+

Python is required to run erk.

**Check version:**

```bash
python3 --version  # Should show 3.10 or higher
```

**Install:** [python.org/downloads](https://python.org/downloads)

### Claude Code

Claude Code is Anthropic's official CLI for Claude. Erk uses it as the AI-powered planning and implementation engine.

**Check installation:**

```bash
claude --version
```

**Install:** See [Claude Code installation guide](https://docs.anthropic.com/en/docs/claude-code/overview)

### uv

uv is a fast Python package installer and environment manager. Erk uses it for installation and dependency management.

**Check installation:**

```bash
uv --version
```

**Install:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or see [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)

### GitHub CLI (gh)

The GitHub CLI is required for pull request operations, issue management, and GitHub integration.

**Check installation:**

```bash
gh --version
```

**Install:**

```bash
# macOS
brew install gh

# Or see https://cli.github.com/
```

After installation, authenticate with GitHub:

```bash
gh auth login
```

## Verification

Verify all prerequisites are installed:

```bash
python3 --version && claude --version && uv --version && gh --version
```

You should see version output for each tool.

## See Also

- [Installation](installation.md) - Next step after prerequisites
