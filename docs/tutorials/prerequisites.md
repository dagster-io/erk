# Prerequisites

Tools you need before installing erk.

Erk orchestrates several tools to enable plan-oriented agentic engineering. This guide helps you install and verify each one.

## Required Tools

### Python 3.11+

Erk is a Python CLI tool. You need Python 3.11 or higher.

**Check your version:**

```bash
python --version
```

You should see `Python 3.11.x` or higher (3.12, 3.13 also work).

If you need to install Python, see [Install Python](https://www.python.org/downloads/).

### Claude Code CLI

Claude Code is the AI agent that powers erk's planning and implementation. You need an active Anthropic account with API access.

**Install:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Verify:**

```bash
claude --version
```

You should see output like `claude-code 1.x.x`.

**First-time setup:**

When you first run `claude`, you'll be prompted to authenticate with your Anthropic account. Follow the browser prompts to complete setup.

**Troubleshooting:**

- If you see authentication errors, run `claude` and follow the login prompts

### uv (Python Package Manager)

Erk uses uv for fast, reproducible Python package management. It's significantly faster than pip and ensures consistent environments.

**Install:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verify:**

```bash
uv --version
```

You should see output like `uv 0.x.x`.

**Why uv instead of pip?**

- **Speed**: 10-100x faster than pip
- **Reproducibility**: Lockfiles ensure consistent installs
- **Simplicity**: Handles Python version management too

### GitHub CLI

The GitHub CLI (`gh`) enables erk to create issues, PRs, and interact with your repositories programmatically.

**macOS (Homebrew):**

```bash
brew install gh
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt install gh
```

**Verify installation:**

```bash
gh --version
```

You should see output like `gh version 2.x.x`.

**Authenticate with GitHub:**

```bash
gh auth login
```

Follow the prompts to authenticate via browser or token.

**Verify authentication:**

```bash
gh auth status
```

You should see output confirming you're logged into github.com.

**Troubleshooting:**

- If `gh auth status` shows "not logged in", run `gh auth login` again
- For GitHub Enterprise, use `gh auth login --hostname your-enterprise.com`

## Optional Enhancements

These tools unlock additional features but are not required to start:

### Graphite (gt)

Graphite enables **stacked PRs**—a workflow where you build features as a stack of dependent branches. This is powerful for large features that benefit from incremental review.

**What it enables:**

- Stack multiple PRs that depend on each other
- Rebase entire stacks with a single command
- Track stack status in erk dashboard

See [Graphite Integration](graphite-integration.md) for setup instructions.

### Shell Integration

Shell integration enables **seamless directory switching** when you navigate between worktrees. Without it, you need to manually `cd` after switching branches.

**What it enables:**

- Automatic directory changes when switching worktrees
- `erk br co <branch>` changes your shell's working directory

See [Shell Integration](shell-integration.md) for setup instructions.

## Quick Reference

| Tool       | Install Command                                           | Verify Command     |
| ---------- | --------------------------------------------------------- | ------------------ |
| Python     | [python.org/downloads](https://www.python.org/downloads/) | `python --version` |
| Claude CLI | `curl -fsSL https://claude.ai/install.sh \| bash`         | `claude --version` |
| uv         | `curl -LsSf https://astral.sh/uv/install.sh \| sh`        | `uv --version`     |
| GitHub CLI | `brew install gh`                                         | `gh --version`     |

## Next Steps

Once all required tools are installed and verified:

- [Installation](installation.md) - Install erk itself
