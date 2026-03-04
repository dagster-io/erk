# Plan: Switch CI Python setup to astral-sh/setup-uv

## Context

The `docs-check` CI job failed with a 15-minute timeout trying to download `cpython-3.13.12` from python.org. This happens because `setup-python-uv` uses `actions/setup-python@v5`, which downloads Python from python.org when the version isn't pre-cached on the GitHub runner. Meanwhile, the remote workflows (`erk-remote-setup`) already use `astral-sh/setup-uv@v5`, which handles Python installation through uv with built-in caching.

## Problem

The `setup-python-uv` composite action:
1. Uses `actions/setup-python@v5` — downloads Python from python.org (can timeout)
2. Installs uv via `pip install uv` — slow, no caching
3. Has no uv dependency cache — re-downloads packages every run

## Solution

Replace `setup-python-uv` to use `astral-sh/setup-uv@v5`, which:
- Installs uv directly (no pip needed)
- Has built-in dependency caching by default
- Lets uv manage Python installation (uv downloads Python itself, with its own cache)
- Is already proven in `erk-remote-setup`

## Changes

### 1. Update `.github/actions/setup-python-uv/action.yml`

Replace the current implementation:

```yaml
# Before
- uses: actions/setup-python@v5
  with:
    python-version: ${{ inputs.python-version }}
- name: Install uv
  shell: bash
  run: pip install uv
- name: Install dependencies
  shell: bash
  run: uv sync --python ${{ inputs.python-version }}
```

With:

```yaml
# After
- uses: astral-sh/setup-uv@v5
  with:
    python-version: ${{ inputs.python-version }}
- name: Install dependencies
  shell: bash
  run: uv sync --python ${{ inputs.python-version }}
```

`astral-sh/setup-uv@v5` accepts a `python-version` input that tells uv which Python to install. The built-in cache covers both the uv binary and the dependency cache (`~/.cache/uv/`).

### 2. Update autofix job in `.github/workflows/ci.yml` (lines 304-311)

The autofix job inlines its own Python setup (can't use composite actions from checkout for security). Replace:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- name: Install uv
  run: pip install uv
```

With:

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    python-version: "3.12"
```

## Files to modify

- `.github/actions/setup-python-uv/action.yml`
- `.github/workflows/ci.yml` (autofix job, lines ~304-311)

## Verification

- Push to a branch and verify all CI jobs pass
- Confirm faster setup times in CI logs (uv install + dependency sync should be faster)
- Check that the matrix Python versions (3.11, 3.12, 3.13, 3.14) all work with uv-managed Python
