"""Click parameter type for PR references.

Accepts plain numbers, GitHub PR URLs, and Graphite PR URLs.
"""

import click

from erk_shared.gateway.github.parsing import parse_pr_ref


class PrRefParamType(click.ParamType):
    """Click parameter type that accepts PR numbers or PR URLs.

    Accepts:
    - Plain numbers: "123"
    - GitHub PR URLs: "https://github.com/owner/repo/pull/123"
    - Graphite PR URLs: "https://app.graphite.dev/github/pr/owner/repo/123"

    Converts all formats to an integer PR number.
    """

    name = "pr_ref"

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> int:
        """Convert PR reference string to PR number.

        Args:
            value: PR reference (number or URL)
            param: Click parameter (for error reporting)
            ctx: Click context (for error reporting)

        Returns:
            PR number as int

        Raises:
            click.exceptions.BadParameter: If value is not a valid PR reference
        """
        if isinstance(value, int):
            return value
        pr_number = parse_pr_ref(value)
        if pr_number is not None:
            return pr_number
        self.fail(
            f"'{value}' is not a valid PR reference.\n\n"
            "Accepted formats:\n"
            "  • Plain number: 123\n"
            "  • GitHub URL: https://github.com/owner/repo/pull/123\n"
            "  • Graphite URL: https://app.graphite.dev/github/pr/owner/repo/123",
            param,
            ctx,
        )


PR_REF = PrRefParamType()
