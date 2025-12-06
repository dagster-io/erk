---
title: Session Auto-Selection Logic
read_when:
  - "working with extraction plan commands"
  - "implementing session selection logic"
  - "understanding automated session selection"
---

# Session Auto-Selection Logic

Commands that analyze sessions use consistent auto-selection logic to avoid prompting users in automated workflows.

## Decision Tree

```
Is on trunk (main/master)?
├─ YES: Use current session only
└─ NO: Check current session size
    ├─ Current session is substantial (≥1KB)
    │   └─ Use current session
    └─ Current session is trivial (<1KB)
        ├─ Exactly 1 substantial session exists
        │   └─ Auto-select that session
        └─ 2+ substantial sessions exist
            ├─ Automated command (raw extraction)
            │   └─ Auto-select ALL substantial sessions
            └─ Interactive command (analyzed extraction)
                └─ Prompt user to choose
```

## Rationale

**Why auto-select on trunk:**

- Trunk sessions are typically interactive development
- Current session has full context

**Why detect trivial sessions:**

- Common pattern: User launches fresh session just to run extraction command
- Trivial session has no useful content to extract
- Previous sessions contain the actual work

**Why automated commands skip prompts:**

- Used by `erk pr land --extract` in scripted workflows
- Must complete without user interaction
- Safe default: analyze all substantial work from branch

## Implementation

Use `dot-agent run erk list-sessions --min-size 1024`:

```python
result = run("dot-agent run erk list-sessions --min-size 1024")
data = json.loads(result)

if data["branch_context"]["is_on_trunk"]:
    # Use current session
    session_ids = [data["current_session_id"]]
elif data["current_session_id"] not in [s["session_id"] for s in data["sessions"]]:
    # Current session is trivial (filtered out)
    if len(data["sessions"]) == 1:
        session_ids = [data["sessions"][0]["session_id"]]
    else:
        # Multiple substantial sessions
        session_ids = [s["session_id"] for s in data["sessions"]]  # or prompt
```

## Related

- List Sessions Command: `packages/dot-agent-kit/.../list_sessions.py`
- Session Size Filtering: [docs/agent/sessions/size-filtering.md](size-filtering.md)
