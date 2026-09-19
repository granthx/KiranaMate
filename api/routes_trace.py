"""
Real-time Trace & Activity Stream API Routes
Allows the frontend dashboard to receive live agent node traces and WhatsApp events.
"""
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from core.trace_bus import trace_bus

router = APIRouter()


@router.get("/stream")
async def trace_stream(request: Request):
    """
    Server-Sent Events (SSE) stream for live agent traces and WhatsApp interactions.
    """
    async def event_generator():
        async for chunk in trace_bus.subscribe():
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/events")
async def get_trace_events(since_id: int = Query(0, description="Fetch events with id > since_id")):
    """
    Polling fallback for dashboard to retrieve events since last seen ID.
    """
    events = trace_bus.get_events(since_id=since_id)
    latest_id = events[-1]["id"] if events else since_id
    return {
        "events": events,
        "latest_id": latest_id,
        "count": len(events),
    }
