# Session JSONL Format

Each session is stored as a single `.jsonl` file (JSON Lines format).

## File Format

- One JSON object per line
- Lines are ordered by time (oldest first)
- Each line has a `type` field indicating the message type

```
┌─────────────────────────────────────────────────────────────┐
│                    Session File (.jsonl)                     │
├─────────────────────────────────────────────────────────────┤
│ Line 1: summary    {type, summary, leafUuid}                │
│ Line 2: snapshot   {type, messageId, snapshot, ...}         │
│ Line 3: user       {type, sessionId, uuid, message, ...}    │
│ Line 4: assistant  {type, sessionId, uuid, message, ...}    │
│ Line 5: user       {type, sessionId, uuid, message, ...}    │
│ ...                                                          │
└─────────────────────────────────────────────────────────────┘
```

## Message Types

| Type        | Description                             |
| ----------- | --------------------------------------- |
| `summary`   | Session metadata, appears first in file |
| `snapshot`  | Checkpoint of message state             |
| `user`      | User message (prompt or tool result)    |
| `assistant` | Assistant response                      |

## The Summary Line

The first line in a session file is the summary:

```json
{
  "type": "summary",
  "summary": "Brief description of the session",
  "leafUuid": "uuid-of-last-message",
  "version": "1"
}
```

| Field      | Description                                  |
| ---------- | -------------------------------------------- |
| `type`     | Always `"summary"`                           |
| `summary`  | Human-readable session description           |
| `leafUuid` | UUID of the most recent message (thread tip) |
| `version`  | Format version                               |

## Message Threading

Messages form a linked list using `uuid` and `parentUuid`:

```
                    ┌──────────────┐
                    │   summary    │
                    │ leafUuid ────┼──────────────────────┐
                    └──────────────┘                      │
                                                          ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│    user      │───▶│  assistant   │───▶│    user      │
│ uuid: A      │    │ parentUuid:A │    │ parentUuid:B │
│ parentUuid:∅ │    │ uuid: B      │    │ uuid: C      │
└──────────────┘    └──────────────┘    └──────────────┘
```

- **First message**: `parentUuid` is empty/null
- **Subsequent messages**: `parentUuid` points to the previous message
- **summary.leafUuid**: Points to the most recent message in the thread

## Reconstructing Conversation Order

To reconstruct a conversation:

1. Parse the summary line to get `leafUuid`
2. Build a map of `uuid -> message`
3. Start at `leafUuid`, follow `parentUuid` links back to root
4. Reverse the chain to get chronological order

```python
def get_conversation(messages, leaf_uuid):
    by_uuid = {m["uuid"]: m for m in messages if "uuid" in m}
    chain = []
    current = leaf_uuid
    while current:
        msg = by_uuid.get(current)
        if not msg:
            break
        chain.append(msg)
        current = msg.get("parentUuid")
    return list(reversed(chain))
```

## Snapshot Messages

Snapshots capture message state at a point in time:

```json
{
  "type": "snapshot",
  "messageId": "uuid",
  "snapshot": "user" | "assistant",
  "isExtensionMessage": false,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

These are bookkeeping records used by Claude Code internally.
