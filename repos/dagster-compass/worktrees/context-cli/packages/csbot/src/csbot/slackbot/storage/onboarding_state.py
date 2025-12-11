"""Onboarding state tracking for idempotent onboarding flow."""

import json
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class BotInstanceType(str, Enum):
    """Bot instance type enumeration.

    Determines the feature set and context engine behavior for a bot instance.
    - STANDARD: Full-featured bot with read-write context store access.
      Also used for prospector bots (detected via connection configuration).
    - COMMUNITY_PROSPECTOR: Read-only bot with ICP-driven candidate sourcing with community mode enabled
    """

    @staticmethod
    def from_db_value(value: str) -> "BotInstanceType":
        if value == "community_prospector":
            return BotInstanceType.COMMUNITY_PROSPECTOR
        elif value == "standard" or value == "prospector":
            return BotInstanceType.STANDARD
        else:
            raise ValueError(f"Invalid bot instance type: {value}")

    STANDARD = "standard"
    COMMUNITY_PROSPECTOR = "community_prospector"


class ProspectorDataType(str, Enum):
    """Data type for prospector bot instances.

    Determines the type of data and system prompt customization:
    - SALES: Focus on sales prospects, companies, and deals
    - RECRUITING: Focus on candidate sourcing and recruitment
    - INVESTING: Focus on investment opportunities and portfolio research
    """

    SALES = "sales"
    RECRUITING = "recruiting"
    INVESTING = "investing"


class OnboardingStep(str, Enum):
    """Onboarding flow steps in order of execution."""

    INITIALIZED = "initialized"
    SLACK_TEAM_CREATED = "slack_team_created"
    CHANNELS_LISTED = "channels_listed"
    ADMINS_INVITED = "admins_invited"
    BOT_IDS_RETRIEVED = "bot_ids_retrieved"
    CONTEXTSTORE_REPO_CREATED = "contextstore_repo_created"
    STRIPE_CUSTOMER_CREATED = "stripe_customer_created"
    STRIPE_SUBSCRIPTION_CREATED = "stripe_subscription_created"
    ORGANIZATION_CREATED = "organization_created"
    TOS_RECORDED = "tos_recorded"
    BOT_INSTANCE_CREATED = "bot_instance_created"
    CHANNELS_ASSOCIATED = "channels_associated"
    SLACK_CONNECT_SENT = "slack_connect_sent"
    SLACK_CONNECT_ACCEPTED = "slack_connect_accepted"
    COMPLETED = "completed"
    # Deprecated - No longer triggered by new onboarding flow (governance channel reconciler handles these)
    COMPASS_CHANNEL_CREATED = "compass_channel_created"
    GOVERNANCE_CHANNEL_CREATED = "governance_channel_created"
    BOTS_INVITED_TO_COMPASS = "bots_invited_to_compass"
    BOTS_INVITED_TO_GOVERNANCE = "bots_invited_to_governance"
    # Deprecated - Old onboarding flows
    MINIMAL_ONBOARDING_COMPLETED = "minimal_onboarding_completed"
    PROSPECTOR_ICP_STORED = "prospector_icp_stored"
    PROSPECTOR_COMBINED_CHANNEL_CREATED = "prospector_combined_channel_created"
    PROSPECTOR_CONNECTION_CREATED = "prospector_connection_created"
    PROSPECTOR_CONNECTION_ASSOCIATED = "prospector_connection_associated"

    @classmethod
    def all_steps(cls) -> list["OnboardingStep"]:
        """Get all active steps in execution order (excludes deprecated steps)."""
        return [
            cls.INITIALIZED,
            cls.SLACK_TEAM_CREATED,
            cls.CHANNELS_LISTED,
            cls.ADMINS_INVITED,
            cls.BOT_IDS_RETRIEVED,
            cls.CONTEXTSTORE_REPO_CREATED,
            cls.STRIPE_CUSTOMER_CREATED,
            cls.STRIPE_SUBSCRIPTION_CREATED,
            cls.ORGANIZATION_CREATED,
            cls.TOS_RECORDED,
            cls.BOT_INSTANCE_CREATED,
            cls.CHANNELS_ASSOCIATED,
            cls.SLACK_CONNECT_SENT,
            cls.SLACK_CONNECT_ACCEPTED,
            cls.COMPLETED,
        ]


class OnboardingState(BaseModel):
    """Onboarding state model for tracking progress through the onboarding flow."""

    id: int | None = None
    email: str
    organization_name: str
    team_domain: str | None = None
    team_name: str | None = None

    # Progress tracking
    current_step: OnboardingStep = OnboardingStep.INITIALIZED
    completed_steps: list[OnboardingStep] = []
    processing_started_at: datetime | None = None

    # Slack resources
    slack_team_id: str | None = None
    general_channel_id: str | None = None
    compass_channel_id: str | None = None
    compass_channel_name: str | None = None
    governance_channel_id: str | None = None
    governance_channel_name: str | None = None

    # Bot user IDs
    dev_tools_bot_user_id: str | None = None
    compass_bot_user_id: str | None = None

    # External resources
    contextstore_repo_name: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    organization_id: int | None = None
    compass_bot_instance_id: int | None = None

    # Metadata
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def is_step_completed(self, step: OnboardingStep) -> bool:
        """Check if a specific step has been completed."""
        return step in self.completed_steps

    def with_step(self, step: OnboardingStep, **fields) -> "OnboardingState":
        """Return a new state with the step completed and additional fields updated.

        Args:
            step: The step to mark as completed
            **fields: Additional fields to update (e.g., slack_team_id="T123")

        Returns:
            New OnboardingState instance with updates applied
        """
        new_completed = self.completed_steps.copy()
        if step not in new_completed:
            new_completed.append(step)

        return self.model_copy(
            update={
                "current_step": step,
                "completed_steps": new_completed,
                "updated_at": datetime.now(),
                **fields,
            }
        )

    def to_db_dict(self) -> dict:
        """Convert to dictionary for database storage with JSON background_onboarding_data field."""
        # Serialize all fields except the lookup keys and timestamps to JSON
        background_onboarding_data = {
            "team_domain": self.team_domain,
            "team_name": self.team_name,
            "current_step": self.current_step.value,
            "completed_steps": [step.value for step in self.completed_steps],
            "processing_started_at": self.processing_started_at.isoformat()
            if self.processing_started_at
            else None,
            "slack_team_id": self.slack_team_id,
            "general_channel_id": self.general_channel_id,
            "compass_channel_id": self.compass_channel_id,
            "compass_channel_name": self.compass_channel_name,
            "governance_channel_id": self.governance_channel_id,
            "governance_channel_name": self.governance_channel_name,
            "dev_tools_bot_user_id": self.dev_tools_bot_user_id,
            "compass_bot_user_id": self.compass_bot_user_id,
            "contextstore_repo_name": self.contextstore_repo_name,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "organization_id": self.organization_id,
            "compass_bot_instance_id": self.compass_bot_instance_id,
            "error_message": self.error_message,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

        return {
            "email": self.email,
            "organization_name": self.organization_name,
            "background_onboarding_data": json.dumps(background_onboarding_data),
        }

    @classmethod
    def from_db_row(cls, row: tuple) -> "OnboardingState":
        """Create OnboardingState from database row with JSON background_onboarding_data field.

        Args:
            row: Tuple of (id, email, organization_name, background_onboarding_data, created_at, updated_at)
        """
        id, email, organization_name, background_onboarding_data_json, created_at, updated_at = row

        data = json.loads(background_onboarding_data_json)

        # Parse datetime fields
        processing_started_at = (
            datetime.fromisoformat(data["processing_started_at"])
            if data.get("processing_started_at")
            else None
        )
        completed_at = (
            datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )

        # Parse completed steps
        completed_steps = [OnboardingStep(step) for step in data.get("completed_steps", [])]

        return cls(
            id=id,
            email=email,
            organization_name=organization_name,
            team_domain=data.get("team_domain"),
            team_name=data.get("team_name"),
            current_step=OnboardingStep(data.get("current_step", "initialized")),
            completed_steps=completed_steps,
            processing_started_at=processing_started_at,
            slack_team_id=data.get("slack_team_id"),
            general_channel_id=data.get("general_channel_id"),
            compass_channel_id=data.get("compass_channel_id"),
            compass_channel_name=data.get("compass_channel_name"),
            governance_channel_id=data.get("governance_channel_id"),
            governance_channel_name=data.get("governance_channel_name"),
            dev_tools_bot_user_id=data.get("dev_tools_bot_user_id"),
            compass_bot_user_id=data.get("compass_bot_user_id"),
            contextstore_repo_name=data.get("contextstore_repo_name"),
            stripe_customer_id=data.get("stripe_customer_id"),
            stripe_subscription_id=data.get("stripe_subscription_id"),
            organization_id=data.get("organization_id"),
            compass_bot_instance_id=data.get("compass_bot_instance_id"),
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            error_message=data.get("error_message"),
        )
