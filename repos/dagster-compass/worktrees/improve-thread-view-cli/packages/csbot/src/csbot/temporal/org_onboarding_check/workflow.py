"""Org Onboarding Check Workflow.

This workflow validates that an organization has successfully completed all onboarding steps
and that resources are properly configured. It checks:
- Onboarding state completion
- Slack workspace and channels
- GitHub contextstore repository
- Stripe billing setup
- Database records (organization, bot instances)
- TOS acceptance
"""

from datetime import timedelta
from typing import Literal

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from csbot.temporal import constants


class OrgOnboardingCheckInput(BaseModel):
    """Input for the org onboarding check workflow.

    Attributes:
        organization_id: The ID of the organization to validate.
    """

    organization_id: int


class ValidationIssue(BaseModel):
    """A specific validation issue found during checks.

    Attributes:
        check_name: The name of the check that failed.
        severity: The severity level (error or warning).
        message: Description of the issue.
    """

    check_name: str
    severity: Literal["error", "warning"]
    message: str


class OrgOnboardingCheckSuccess(BaseModel):
    """Successful validation result.

    Attributes:
        type: Discriminator field.
        organization_id: The organization ID that was validated.
        all_checks_passed: Whether all validation checks passed.
        issues: List of validation issues found (may be empty if all passed).
    """

    type: Literal["success"] = "success"
    organization_id: int
    all_checks_passed: bool
    issues: list[ValidationIssue]


class OrgOnboardingCheckOrganizationNotFound(BaseModel):
    """Organization not found error.

    Attributes:
        type: Discriminator field.
        organization_id: The organization ID that was not found.
    """

    type: Literal["organization_not_found"] = "organization_not_found"
    organization_id: int


OrgOnboardingCheckResult = OrgOnboardingCheckSuccess | OrgOnboardingCheckOrganizationNotFound


@workflow.defn(name=constants.Workflow.ORG_ONBOARDING_CHECK_WORKFLOW_NAME.value)
class OrgOnboardingCheckWorkflow:
    """Workflow to validate organization onboarding completion.

    This workflow orchestrates validation activities to ensure an organization
    has been properly set up through the onboarding process.
    """

    @workflow.run
    async def run(self, args: OrgOnboardingCheckInput) -> OrgOnboardingCheckResult:
        """Execute the org onboarding validation workflow.

        Args:
            args: Input containing the organization_id to validate.

        Returns:
            Result indicating validation success or failure with details.
        """
        workflow.logger.info(
            f"Starting org onboarding check for organization_id={args.organization_id}"
        )

        # Execute the validation activity
        result = await workflow.execute_activity(
            constants.Activity.VALIDATE_ORG_ONBOARDING_ACTIVITY_NAME.value,
            args,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=OrgOnboardingCheckResult,  # pyright: ignore
        )

        if result.type == "success":
            if result.all_checks_passed:
                workflow.logger.info(
                    f"All onboarding checks passed for organization_id={args.organization_id}"
                )
            else:
                workflow.logger.warning(
                    f"Onboarding validation completed with {len(result.issues)} issues "
                    f"for organization_id={args.organization_id}"
                )
        else:
            workflow.logger.error(
                f"Organization {args.organization_id} not found during validation"
            )

        return result
