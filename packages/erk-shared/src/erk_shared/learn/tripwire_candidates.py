"""Parse tripwire candidates from learn plan markdown.

Learn plans may contain a `## Tripwire Additions` section with proposed
tripwires for documentation files. This module extracts those candidates
for promotion to actual frontmatter tripwires.
"""

import logging
import re
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TripwireCandidate:
    """A tripwire candidate extracted from a learn plan.

    Attributes:
        action: The action pattern to detect (e.g., "writing to /tmp/").
        warning: The warning message to display when action is detected.
        target_doc_path: Relative path to the target doc (e.g., "architecture/foo.md").
    """

    action: str
    warning: str
    target_doc_path: str


def extract_tripwire_candidates(plan_body: str) -> list[TripwireCandidate]:
    """Parse ## Tripwire Additions section from learn plan markdown.

    Looks for a section structured like:

        ## Tripwire Additions

        ### For `architecture/foo.md`

        ```yaml
        tripwires:
          - action: "doing X"
            warning: "Do Y instead."
        ```

    Args:
        plan_body: Full learn plan markdown content.

    Returns:
        List of TripwireCandidate objects. Empty list on any parse failure.
    """
    # Find the ## Tripwire Additions section
    section_match = re.search(
        r"^## Tripwire Additions\s*\n(.*?)(?=^## |\Z)",
        plan_body,
        re.MULTILINE | re.DOTALL,
    )
    if section_match is None:
        return []

    section_content = section_match.group(1)

    # Find all ### For `<path>` subsections with their content
    subsection_pattern = re.compile(
        r"^### For `([^`]+)`\s*\n(.*?)(?=^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )

    candidates: list[TripwireCandidate] = []

    for sub_match in subsection_pattern.finditer(section_content):
        target_doc_path = sub_match.group(1)
        subsection_body = sub_match.group(2)

        # Extract YAML from fenced code blocks
        yaml_pattern = re.compile(
            r"```ya?ml\s*\n(.*?)```",
            re.DOTALL,
        )

        for yaml_match in yaml_pattern.finditer(subsection_body):
            yaml_content = yaml_match.group(1)
            parsed = _parse_tripwire_yaml(yaml_content, target_doc_path)
            candidates.extend(parsed)

    return candidates


def _parse_tripwire_yaml(
    yaml_content: str,
    target_doc_path: str,
) -> list[TripwireCandidate]:
    """Parse YAML content containing tripwire entries.

    Args:
        yaml_content: Raw YAML string from a code block.
        target_doc_path: The target doc path for these tripwires.

    Returns:
        List of TripwireCandidate objects. Empty list on parse failure.
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        logger.debug("Failed to parse YAML for tripwire candidates in %s", target_doc_path)
        return []

    if not isinstance(data, dict):
        return []

    tripwires_list = data.get("tripwires")
    if not isinstance(tripwires_list, list):
        return []

    results: list[TripwireCandidate] = []
    for entry in tripwires_list:
        if not isinstance(entry, dict):
            continue
        action = entry.get("action")
        warning = entry.get("warning")
        if not isinstance(action, str) or not isinstance(warning, str):
            continue
        results.append(
            TripwireCandidate(
                action=action,
                warning=warning,
                target_doc_path=target_doc_path,
            )
        )

    return results
