"""Claude installation abstraction layer.

This package provides a domain-driven interface for Claude installation operations.
All filesystem details are hidden behind the ClaudeInstallation ABC.

Import directly from submodules:
- abc: ClaudeInstallation, Session, SessionContent, FoundSession
- real: RealClaudeInstallation
- fake: FakeClaudeInstallation, FakeProject, FakeSessionData
"""
