# Plan: Cache Claude Code in GitHub Actions Workflow

## Summary

Add GitHub Actions caching for Claude Code CLI to avoid re-downloading and reinstalling on every workflow run.

## File to Modify

- `.github/workflows/dispatch-erk-queue-git.yml`

## Implementation

### Step 1: Add Cache Step (after checkout, before "Setup all tools")

Insert a new step after line 57 (checkout) and before line 59 ("Setup all tools"):

```yaml
- name: Cache Claude Code
  id: cache-claude
  uses: actions/cache@v4
  with:
    path: |
      ~/.claude
      ~/.local/bin/claude
    key: claude-code-${{ runner.os }}-v1
```

### Step 2: Make Claude Code Installation Conditional

Modify the "Setup all tools" step to skip Claude Code installation on cache hit. Change:

```yaml
# Install Claude Code first (better layer caching)
curl -fsSL https://claude.ai/install.sh | bash
```

To:

```yaml
# Install Claude Code (skip if cached)
if [ "${{ steps.cache-claude.outputs.cache-hit }}" != "true" ]; then
  curl -fsSL https://claude.ai/install.sh | bash
else
  echo "Claude Code restored from cache"
  echo "$HOME/.local/bin" >> $GITHUB_PATH
fi
```

## Cache Key Strategy

- `claude-code-${{ runner.os }}-v1` - bump version suffix to invalidate cache when needed
- OS-specific to handle platform differences

## Notes

- Cache restores files but not PATH modifications, so we add to GITHUB_PATH on cache hit
- The `~/.claude` directory contains the installation; `~/.local/bin/claude` is the binary
- Cache invalidation: bump `v1` suffix when Claude Code updates are needed