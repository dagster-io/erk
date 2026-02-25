from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestedReply:
    label: str
    action_id: str
    value: str


CHAT_SUGGESTED_REPLIES: tuple[SuggestedReply, ...] = (
    SuggestedReply(
        label="Show Plans",
        action_id="suggested_reply_plan_list",
        value="plan list",
    ),
    SuggestedReply(
        label="Tell me more",
        action_id="suggested_reply_tell_me_more",
        value="chat tell me more about that",
    ),
    SuggestedReply(
        label="Start fresh",
        action_id="suggested_reply_start_fresh",
        value="chat hello, what can you help me with?",
    ),
)


def build_suggested_replies_blocks(
    *, replies: tuple[SuggestedReply, ...]
) -> list[dict[str, object]]:
    elements: list[dict[str, object]] = []
    for reply in replies:
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": reply.label},
                "action_id": reply.action_id,
                "value": reply.value,
            }
        )
    return [{"type": "actions", "elements": elements}]


def build_selected_reply_blocks(*, selected_label: str, user_id: str) -> list[dict[str, object]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}> selected: *{selected_label}*",
            },
        }
    ]
