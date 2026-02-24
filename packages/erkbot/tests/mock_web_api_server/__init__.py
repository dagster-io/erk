"""Mock Slack Web API server for integration testing.

Adapted from bolt-python's test infrastructure. Provides a local HTTP server
that simulates Slack API endpoints so integration tests can dispatch through
a real AsyncApp without needing a Slack connection.
"""
