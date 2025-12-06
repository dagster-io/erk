# Suppress UV Hardlink Warning in Planner Codespaces

## Problem

When running `erk planner` to connect to a GitHub Codespace, the following warning appears:

```
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
         If the cache and target directories are on different filesystems, hardlinking may not be supported.
         If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.
```

This occurs because the uv cache and target directories are on different filesystems in the codespace environment.

## Solution

Add `UV_LINK_MODE=copy` environment variable to `.devcontainer/devcontainer.json` using the `remoteEnv` property.

## Changes

### File: `.devcontainer/devcontainer.json`

Add `remoteEnv` section to set the UV_LINK_MODE environment variable:

```json
{
  "name": "erk-planning",
  "image": "mcr.microsoft.com/devcontainers/python:3.13",
  "features": {
    "ghcr.io/devcontainers/features/github-cli:1": {},
    "ghcr.io/devcontainers/features/sshd:1": {
      "version": "latest"
    }
  },
  "remoteEnv": {
    "UV_LINK_MODE": "copy"
  },
  "postCreateCommand": "curl -fsSL https://claude.ai/install.sh | bash && pip install uv && uv sync",
  "customizations": {
    "codespaces": {
      "permissions": {
        "contents": "write",
        "pull_requests": "write",
        "workflows": "write",
        "actions": "write",
        "statuses": "write",
        "deployments": "write",
        "members": "read"
      }
    }
  }
}
```

## Why This Approach

- **Targeted**: Only affects planner codespaces, not local development
- **Clean**: Uses standard devcontainer configuration rather than inline command modifications
- **Future-proof**: Will apply to all uv commands in the codespace, including future additions

## Note

Existing codespaces will need to be rebuilt to pick up this change. New codespaces will automatically have the environment variable set.