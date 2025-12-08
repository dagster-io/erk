# Repository Setup

One-time setup for enabling erk in a repository.

## Install Kits

```bash
dot-agent kit install erk
dot-agent kit install devrun
dot-agent kit install dignified-python
dot-agent kit install gt
```

These kits provide:
- **erk** - Plan management commands, skills, and hooks
- **devrun** - Development tool runner (pytest, pyright, ruff, etc.)
- **dignified-python** - Python coding standards and patterns
- **gt** - Graphite stack management

## Initialize Erk

```bash
erk init
```

Creates the `erk.toml` configuration file.

## Update .gitignore

Add:

```
.impl/
```

The `.impl/` directory holds local plan implementation state and should not be committed.
