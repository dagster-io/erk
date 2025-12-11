import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel
from slack_sdk.web.async_client import AsyncWebClient

from csbot.agents.messages import AgentTextMessage
from csbot.agents.protocol import AsyncAgent

if TYPE_CHECKING:
    from csbot.slackbot.storage.interface import SlackbotInstanceStorage


class CompanyInfo(BaseModel):
    name: str
    url: str
    description: str


class EnrichedPerson(BaseModel):
    real_name: str
    job_title: str | None = None
    timezone: str | None = None
    email: str | None = None


@dataclass(frozen=True)
class SlackUserInfo:
    """
    Cached Slack user information.

    Contains the most commonly needed user fields with avatar preference
    logic applied (72px > 48px > 32px).
    """

    real_name: str
    username: str  # Slack username (e.g., "john.doe")
    email: str | None
    avatar_url: str | None
    timezone: str | None
    is_bot: bool
    is_admin: bool
    is_owner: bool
    deleted: bool
    is_restricted: bool
    is_ultra_restricted: bool


async def get_company_info(
    agent: AsyncAgent, company_name: str, company_url: str, company_profile: dict[str, str]
) -> CompanyInfo | None:
    query = urlencode({"query": f"company information for {company_name} at {company_url}"})
    url = f"https://api.ydc-index.io/v1/search?{query}"

    API_KEY = os.getenv("YOU_SEARCH_API_KEY")
    if not API_KEY:
        raise ValueError("YOU_SEARCH_API_KEY is not set")
    headers = {"X-API-Key": API_KEY}

    async with httpx.AsyncClient() as httpx_client:
        response = await httpx_client.get(url, headers=headers)
        response.raise_for_status()
        json_response = response.json()

    summary = await agent.create_completion(
        model=agent.model,
        system="Create a 1 paragraph summary of the company described by the provided information. Return only this paragraph and no other content.",
        messages=[
            AgentTextMessage(
                role="user",
                content=json.dumps(
                    {"web_search_results": json_response, "company_profile": company_profile}
                ),
            )
        ],
    )
    return CompanyInfo(
        name=company_name,
        url=company_url,
        description=summary,
    )


async def get_person_info_from_slack_user_id(
    client: AsyncWebClient, kv_store: "SlackbotInstanceStorage", user_id: str
) -> EnrichedPerson | None:
    prev_person_info = await kv_store.get("person_info", user_id)
    if not prev_person_info:
        person_info = await _get_person_info_from_slack_user_id(client, kv_store, user_id)
        await kv_store.set(
            "person_info",
            user_id,
            json.dumps({"value": person_info.model_dump(mode="json") if person_info else None}),
            14 * 24 * 60 * 60,  # 14 days - balance between fresh data and rate limit protection
        )
        return person_info
    else:
        value = json.loads(prev_person_info)["value"]
        if not value:
            return None
        person_info = EnrichedPerson.model_validate(value)
        return person_info


async def _get_person_info_from_slack_user_id(
    client: AsyncWebClient, kv_store: "SlackbotInstanceStorage", user_id: str
) -> EnrichedPerson | None:
    # Use cached user info (already includes locale data)
    user_info = await get_cached_user_info(client, kv_store, user_id)
    if not user_info:
        return None

    # Skip bots
    if user_info.is_bot:
        return None

    # Only attempt person enrichment if we have an email
    job_title: str | None = None
    if user_info.email:
        json_response = await enrich_person({"name": user_info.real_name, "email": user_info.email})
        if json_response:
            job_title = json_response.get("job_title")

    # Always return EnrichedPerson even if email is missing (for analytics)
    return EnrichedPerson(
        job_title=job_title,
        timezone=user_info.timezone,
        real_name=user_info.real_name,
        email=user_info.email,
    )


async def enrich_person(fields: dict[str, str]) -> dict[str, str] | None:
    API_KEY = os.getenv("PEOPLEDATALABS_API_KEY")
    if not API_KEY:
        raise ValueError("PEOPLEDATALABS_API_KEY is not set")
    # Set the Person Enrichment API URL
    PDL_URL = "https://api.peopledatalabs.com/v5/person/enrich"

    # Set headers
    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }
    PARAMS = {"min_likelihood": "6", **fields}

    # Pass the parameters object to the Person Enrichment API
    async with httpx.AsyncClient() as httpx_client:
        response = await httpx_client.get(PDL_URL, headers=HEADERS, params=PARAMS)
        if response.status_code != 200:
            return None
        json_response = response.json()

    return json_response["data"]


async def enrich_company(domain: str) -> dict[str, str] | None:
    API_KEY = os.getenv("PEOPLEDATALABS_API_KEY")
    if not API_KEY:
        raise ValueError("PEOPLEDATALABS_API_KEY is not set")
    # Set the Company Enrichment API URL
    PDL_URL = "https://api.peopledatalabs.com/v5/company/enrich"

    # Create a parameters JSON object
    QUERY_STRING = {"website": domain}

    # Set headers
    HEADERS = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY,
    }

    async with httpx.AsyncClient() as httpx_client:
        response = await httpx_client.get(PDL_URL, headers=HEADERS, params=QUERY_STRING)
        if response.status_code != 200:
            return None
        json_response = response.json()

    return json_response


async def get_company_info_from_domain(agent: AsyncAgent, domain: str) -> CompanyInfo | None:
    enriched_company = await enrich_company(domain)
    if not enriched_company:
        return None

    return await get_company_info(
        agent, enriched_company["name"], enriched_company["website"], enriched_company
    )


async def get_cached_user_info(
    client: AsyncWebClient, kv_store: "SlackbotInstanceStorage", user_id: str
) -> SlackUserInfo | None:
    """
    Get user info from Slack API with 7-day caching (write-through cache).

    This function always fetches user info with include_locale=True to ensure
    complete user data is cached, including timezone and locale information.

    Args:
        client: Slack API client
        kv_store: Key-value store for caching user info
        user_id: The Slack user ID to look up

    Returns:
        SlackUserInfo with real_name, email, and avatar_url (preferring 72px > 48px > 32px),
        or None if user not found
    """
    # Check cache first
    cached_user_info = await kv_store.get("user_info", user_id)
    if cached_user_info:
        cached_data = json.loads(cached_user_info)
        raw_user_info = cached_data.get("value")
        if raw_user_info:
            return _extract_user_info(raw_user_info)
        return None

    # Fetch from Slack API with locale data for complete user information
    response = await client.users_info(user=user_id, include_locale=True)
    if response.get("ok") and response.get("user"):
        user_info: dict = response["user"]  # type: ignore[assignment]
        # Cache for 7 days
        await kv_store.set(
            "user_info",
            user_id,
            json.dumps({"value": user_info}),
            7 * 24 * 60 * 60,  # 7 days in seconds
        )
        return _extract_user_info(user_info)

    return None


def _extract_user_info(raw_user_info: dict) -> SlackUserInfo:
    """Extract SlackUserInfo from raw Slack API user dict."""
    profile = raw_user_info.get("profile", {})

    # Get real_name from profile or fallback to user-level field
    real_name = profile.get("real_name") or raw_user_info.get("real_name") or ""

    # Get username from user-level field (Slack username like "john.doe")
    username = raw_user_info.get("name", "")

    # Get email from profile
    email = profile.get("email")

    # Get avatar with preference: 72px > 48px > 32px
    avatar_url = profile.get("image_72") or profile.get("image_48") or profile.get("image_32")

    # Get timezone from user-level field
    timezone = raw_user_info.get("tz")

    # Get user status fields
    is_bot = raw_user_info.get("is_bot", False)
    is_admin = raw_user_info.get("is_admin", False)
    is_owner = raw_user_info.get("is_owner", False)
    deleted = raw_user_info.get("deleted", False)
    is_restricted = raw_user_info.get("is_restricted", False)
    is_ultra_restricted = raw_user_info.get("is_ultra_restricted", False)

    return SlackUserInfo(
        real_name=real_name,
        username=username,
        email=email,
        avatar_url=avatar_url,
        timezone=timezone,
        is_bot=is_bot,
        is_admin=is_admin,
        is_owner=is_owner,
        deleted=deleted,
        is_restricted=is_restricted,
        is_ultra_restricted=is_ultra_restricted,
    )


async def resolve_user_mentions_in_message(
    client: AsyncWebClient, kv_store: "SlackbotInstanceStorage", message: str
) -> str:
    """
    Resolve all user mentions in a Slack message to include real names.

    Converts <@U123456> to <@U123456> (Real Name) format.

    Args:
        client: Slack API client
        kv_store: Key-value store for caching user info
        message: The message text to process

    Returns:
        The message with resolved user mentions
    """
    # Pattern to match user mentions like <@U123456>
    user_mention_pattern = r"<@([U][0-9A-Z]+)>"

    # First, find all user mentions
    matches = list(re.finditer(user_mention_pattern, message))
    if not matches:
        return message

    # Collect all user IDs that need resolution
    user_ids = [match.group(1) for match in matches]

    # Resolve all user IDs in parallel
    async def resolve_single_user(user_id: str) -> tuple[str, str]:
        """Resolve a single user ID to a formatted mention."""
        # Get user info using existing function
        person_info = await get_person_info_from_slack_user_id(client, kv_store, user_id)
        if person_info:
            parts = []
            if person_info.real_name:
                parts.append(person_info.real_name)
            if person_info.job_title:
                parts.append(person_info.job_title)
            if len(parts) > 0:
                return user_id, f"<@{user_id}> ({', '.join(parts)})"
            else:
                return user_id, f"<@{user_id}>"
        else:
            # Fallback: try to get basic user info from cached Slack API
            user_info = await get_cached_user_info(client, kv_store, user_id)
            if user_info and user_info.real_name:
                return user_id, f"<@{user_id}> ({user_info.real_name})"
        return user_id, f"<@{user_id}>"

    # Resolve all users in parallel
    resolution_tasks = [resolve_single_user(user_id) for user_id in user_ids]
    resolution_results = await asyncio.gather(*resolution_tasks)

    # Build resolved mentions dict
    resolved_mentions = {}
    for user_id, resolved_mention in resolution_results:
        resolved_mentions[user_id] = resolved_mention

    # Replace all mentions in the message
    resolved_message = message
    for user_id, resolved_mention in resolved_mentions.items():
        resolved_message = resolved_message.replace(f"<@{user_id}>", resolved_mention)

    return resolved_message
