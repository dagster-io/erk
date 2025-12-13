"""Shared JWT claims/grants for webapp URL authentication.

This module defines standard permission sets that can be embedded in JWT tokens
for different management URLs. This ensures consistency across billing, connection,
channel management, etc.
"""

from enum import Enum


class Permission(str, Enum):
    """Standard management permissions for admin/management URLs.

    These permissions provide granular access control to billing, connections,
    channels, dataset sync, users, threads, and GitHub authentication features.
    """

    VIEW_BILLING = "view_billing"
    MANAGE_BILLING = "manage_billing"
    VIEW_CHANNELS = "view_channels"
    MANAGE_CHANNELS = "manage_channels"
    VIEW_CONNECTIONS = "view_connections"
    MANAGE_CONNECTIONS = "manage_connections"
    VIEW_CONTEXT_STORE = "view_context_store"
    MANAGE_CONTEXT_STORE = "manage_context_store"
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
