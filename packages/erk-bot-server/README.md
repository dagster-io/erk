# erk-bot-server

FastAPI server for managing Claude CLI sessions.

## Overview

This package provides a REST API for creating and managing Claude CLI sessions, with SSE streaming for real-time responses.

## Installation

```bash
uv pip install -e .
```

## Usage

```bash
erk-bot-server
```

## API Endpoints

- `POST /api/sessions` - Create a new session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{session_id}` - Get session info
- `POST /api/sessions/{session_id}/messages` - Send message (SSE stream)
- `DELETE /api/sessions/{session_id}` - Delete a session
