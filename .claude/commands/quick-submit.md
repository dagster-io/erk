---
description: Quick commit all changes and submit with Graphite
---

# Quick Submit

Quickly commit all changes with a generic "update" message and submit to Graphite.

## Usage

```bash
/quick-submit
```

## Implementation

Run the following commands in sequence:

```bash
git add -A && git commit -a -m update && gt submit
```

## Notes

- This is a shortcut for rapid iteration
- Uses generic "update" commit message
- For proper commit messages, use `/gt:pr-submit` instead
