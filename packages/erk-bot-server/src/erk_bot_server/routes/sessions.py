"""HTTP routes for session management."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from erk_bot_server.context import ServerContext
from erk_bot_server.models.session import Session
from erk_bot_server.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# Request/Response models
class CreateSessionRequest(BaseModel):
    """Request body for creating a session."""

    external_id: str | None = None
    working_directory: str


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    content: str
    timeout_seconds: int = 300


class SessionResponse(BaseModel):
    """Response body for session info."""

    session_id: str
    external_id: str | None
    working_directory: str
    status: str
    created_at: str
    last_activity: str
    message_count: int

    @staticmethod
    def from_session(session: Session) -> "SessionResponse":
        """Convert Session model to response."""
        return SessionResponse(
            session_id=session.session_id,
            external_id=session.external_id,
            working_directory=session.working_directory,
            status=session.status,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            message_count=session.message_count,
        )


class SessionListResponse(BaseModel):
    """Response body for listing sessions."""

    sessions: list[SessionResponse]


# Dependency injection
def get_context(request: Request) -> ServerContext:
    """Get ServerContext from app state."""
    return request.app.state.context


def get_session_service(
    context: Annotated[ServerContext, Depends(get_context)],
) -> SessionService:
    """Get SessionService from context."""
    return SessionService(
        session_store=context.session_store,
        claude_runner=context.claude_runner,
    )


# Routes
@router.post("", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Create a new Claude CLI session."""
    session = await service.create_session(
        external_id=request.external_id,
        working_directory=request.working_directory,
    )
    return SessionResponse.from_session(session)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionListResponse:
    """List all sessions."""
    sessions = await service.list_sessions()
    return SessionListResponse(sessions=[SessionResponse.from_session(s) for s in sessions])


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionResponse:
    """Get session info by ID."""
    session = await service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.from_session(session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> dict[str, bool]:
    """Delete a session."""
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@router.post("/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    service: Annotated[SessionService, Depends(get_session_service)],
) -> EventSourceResponse:
    """Send a message and stream the response via SSE."""

    async def event_generator():
        """Generate SSE events from Claude response."""
        try:
            async for event in service.send_message(
                session_id=session_id,
                content=request.content,
                timeout_seconds=request.timeout_seconds,
            ):
                yield {
                    "event": event.event_type,
                    "data": json.dumps(event.data),
                }
        except ValueError as e:
            # Session not found
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(event_generator())
