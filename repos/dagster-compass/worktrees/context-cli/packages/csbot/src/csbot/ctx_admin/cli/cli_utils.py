from csadmin.utils import get_project_path

from csbot.contextengine.contextstore_protocol import ContextStoreProject
from csbot.csbot_client.csbot_profile import ProjectProfile

# Re-export for backwards compatibility
__all__ = ["get_project_path", "get_default_connection"]


def get_default_connection(profile: ProjectProfile, project: ContextStoreProject) -> str | None:
    """
    Get the default connection when there's only one connection available for the project.

    Args:
        profile: The project profile
        project: The contextstore project

    Returns:
        The connection name if there's exactly one connection, None otherwise
    """
    connections = list(profile.connections.keys())
    if len(connections) == 1:
        return connections[0]
    return None
