---
title: Kit Registry Discovery
read_when:
  - "kit not showing in search"
  - "debugging kit discovery"
  - "understanding registry.yaml"
---

# Kit Registry Discovery

How `dot-agent kit search` finds and lists available kits.

## Discovery Flow

```
dot-agent kit search
    ↓
load_registry()  (io/registry.py)
    ↓
read registry.yaml  (data/registry.yaml)
    ↓
for each entry:
    - BundledKitSource.can_resolve(kit_id)
    - can_resolve() checks if /data/kits/{kit_id}/kit.yaml exists
    - Load manifest from kit.yaml to get version & artifact counts
    ↓
Display results
```

## Key Files

| File                                                              | Purpose                                                |
| ----------------------------------------------------------------- | ------------------------------------------------------ |
| `packages/dot-agent-kit/src/dot_agent_kit/data/registry.yaml`     | Single source of truth for discoverable kits           |
| `packages/dot-agent-kit/src/dot_agent_kit/io/registry.py`         | Loads and parses registry.yaml                         |
| `packages/dot-agent-kit/src/dot_agent_kit/sources/bundled.py`     | `BundledKitSource.can_resolve()` - verifies kit exists |
| `packages/dot-agent-kit/src/dot_agent_kit/commands/kit/search.py` | Search command implementation                          |

## Troubleshooting: Kit Not Appearing

1. **Check registry.yaml** - Is the kit_id listed?
2. **Check kit directory** - Does `data/kits/{kit_id}/` exist?
3. **Check kit.yaml** - Does `data/kits/{kit_id}/kit.yaml` exist?
4. **Check for stale entries** - After kit consolidation, registry.yaml may reference old kit IDs
