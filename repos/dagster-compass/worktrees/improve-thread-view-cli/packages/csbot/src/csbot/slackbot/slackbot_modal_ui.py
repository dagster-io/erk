# Some sort of viewstate

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from slack_sdk.web.async_client import AsyncWebClient

from csbot.slackbot.slackbot_blockkit import Block
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.slackbot.slack_types import SlackInteractivePayload


def remove_nones(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


@dataclass(frozen=True)
class Modal:
    title: str
    blocks: list[Block]
    close: str | None = None
    submit: str | None = None
    clear_on_close: bool = False
    notify_on_close: bool = False

    def to_dict(
        self, callback_id: str, modal_type_name: str, props: Any, state: Any
    ) -> dict[str, Any]:
        return remove_nones(
            {
                "type": "modal",
                "callback_id": callback_id,
                "private_metadata": json.dumps(
                    {
                        "managed_modal_type": modal_type_name,
                        "props": props,
                        "state": state,
                    }
                ),
                "title": {"type": "plain_text", "text": self.title},
                "blocks": [block.to_dict() for block in self.blocks],
                "close": {"type": "plain_text", "text": self.close} if self.close else None,
                "submit": {"type": "plain_text", "text": self.submit} if self.submit else None,
                "clear_on_close": self.clear_on_close,
                "notify_on_close": self.notify_on_close,
            }
        )


class SlackModal[TProps, TState, TServices](ABC):
    def __init__(self):
        self._view_id: str | None = None
        self._callback_id: str | None = None
        self._client: AsyncWebClient | None = None

    def _set_modal_info(self, view_id: str, callback_id: str, client: AsyncWebClient):
        """Internal method to set modal information for updates."""
        self._view_id = view_id
        self._callback_id = callback_id
        self._client = client

    async def update_state(self, props: TProps, state: TState) -> None:
        """Update the modal with new state using views_update."""
        if not self._view_id or not self._callback_id or not self._client:
            raise ValueError("Modal not properly initialized for updates")

        updated_modal = self.render(props, state)
        await self._client.views_update(
            view_id=self._view_id,
            view=updated_modal.to_dict(
                callback_id=self._callback_id,
                modal_type_name=self.get_modal_type_name(),
                props=props,
                state=state,
            ),
        )

    async def on_load(self, services: TServices, props: TProps, state: TState) -> None:
        """Called after the modal is created and displayed.

        Override this method to perform any initialization or data loading
        that should happen after the modal is shown to the user.

        Args:
            services: Service dependencies
            props: Modal properties
            state: Initial modal state
        """

    @abstractmethod
    def get_modal_type_name(self) -> str:
        pass

    @abstractmethod
    def get_initial_state(self, props: TProps) -> TState:
        pass

    @abstractmethod
    def render(self, props: TProps, state: TState) -> Modal:
        pass

    @abstractmethod
    async def handle_event(
        self,
        services: TServices,
        props: TProps,
        state: TState,
        payload: "SlackInteractivePayload",
    ) -> TState:
        pass


@dataclass(frozen=True)
class InteractionPayloadConfig:
    action_id: str
    value: str


class ModalManager:
    def __init__(
        self, client: AsyncWebClient, modal_classes: list[type[SlackModal[Any, Any, Any]]]
    ):
        self.client = client
        self.modals: dict[str, type[SlackModal[Any, Any, Any]]] = {
            modal_class().get_modal_type_name(): modal_class for modal_class in modal_classes
        }

    async def create_modal[TProps, TState, TServices](
        self,
        trigger_id: str,
        channel_id: str,
        modal_class: type[SlackModal[TProps, TState, TServices]],
        props: TProps,
    ):
        modal_id = str(uuid.uuid4())
        callback_id = f"#{normalize_channel_name(channel_id)}|{modal_id}"
        instance = modal_class()
        state = instance.get_initial_state(props)
        modal = instance.render(
            props,
            state,
        )
        if not modal:
            return None
        response = await self.client.views_open(
            trigger_id=trigger_id,
            view=modal.to_dict(callback_id, instance.get_modal_type_name(), props, state),
        )

        # Return the view ID from the response for potential auto-updating
        view_id = response.get("view", {}).get("id")
        return {
            "view_id": view_id,
            "modal_class": modal_class,
            "props": props,
            "state": state,
            "instance": instance,
            "callback_id": callback_id,
        }

    def create_interaction_payload_config[TProps, TState, TServices](
        self,
        modal_class: type[SlackModal[TProps, TState, TServices]],
        props: TProps,
    ) -> InteractionPayloadConfig:
        nonce = str(uuid.uuid4())
        action_id = f"show_managed_modal:{nonce}"
        value = json.dumps(
            {
                "managed_modal_type": modal_class().get_modal_type_name(),
                "props": props,
            }
        )
        return InteractionPayloadConfig(action_id=action_id, value=value)

    async def handle_interactive_message(
        self, services: Any, payload: "SlackInteractivePayload"
    ) -> bool:
        trigger_id = payload.get("trigger_id")

        action_id = (
            payload.get("actions", [{}])[0].get("action_id") if payload.get("actions") else None
        )
        if action_id is not None and action_id.startswith("show_managed_modal:") and trigger_id:
            value = json.loads(payload.get("actions", [{}])[0].get("value", "{}"))
            modal_type_name = value.get("managed_modal_type")
            props = value.get("props")
            channel_id = payload.get("channel", {}).get("id")
            channel_name = None
            if channel_id is not None:
                channel_info = await self.client.conversations_info(channel=channel_id)
                channel_name = channel_info.get("channel", {}).get("name")
            if modal_type_name is not None and props is not None and channel_name is not None:
                if modal_type_name not in self.modals:
                    raise ValueError(f"Modal type name {modal_type_name} not found")
                modal_class = self.modals[modal_type_name]
                modal_info = await self.create_modal(trigger_id, channel_name, modal_class, props)

                # Set modal info for potential updates and call on_load
                if modal_info:
                    from typing import cast

                    instance = cast("SlackModal", modal_info["instance"])
                    view_id = cast("str", modal_info["view_id"])
                    callback_id = cast("str", modal_info["callback_id"])

                    if instance and view_id and callback_id:
                        instance._set_modal_info(view_id, callback_id, self.client)

                        # Call on_load method for any initialization
                        import asyncio

                        asyncio.create_task(instance.on_load(services, props, modal_info["state"]))

                return True

        view = payload.get("view")
        if view is None:
            return False

        callback_id = view.get("callback_id")
        private_metadata = view.get("private_metadata")
        if callback_id is None or private_metadata is None:
            return False

        private_metadata_parsed = json.loads(private_metadata)
        if (
            "managed_modal_type" not in private_metadata_parsed
            or "props" not in private_metadata_parsed
            or "state" not in private_metadata_parsed
        ):
            return False
        modal_type_name = private_metadata_parsed["managed_modal_type"]
        props = private_metadata_parsed["props"]
        state = private_metadata_parsed["state"]
        if modal_type_name not in self.modals:
            raise ValueError(f"Modal type name {modal_type_name} not found")
        modal_class = self.modals[modal_type_name]
        state = await modal_class().handle_event(services, props, state, payload)
        if payload.get("type") in ["view_submission", "view_closed"]:
            # Modal is gone now so we don't need to re-render
            return True
        next_modal = modal_class().render(props, state)
        await self.client.views_update(
            view_id=view["id"],
            view=next_modal.to_dict(callback_id, modal_type_name, props, state),
        )
        return True
