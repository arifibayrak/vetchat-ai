"""
Conversation history endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select

from app.auth import get_current_user
from app import database
from app.models.db import conversations, messages

router = APIRouter()


def _require_db():
    if database.SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not configured")


@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    _require_db()
    async with database.SessionLocal() as session:
        result = await session.execute(
            select(
                conversations.c.id,
                conversations.c.title,
                conversations.c.created_at,
                conversations.c.updated_at,
            )
            .where(conversations.c.user_id == current_user["sub"])
            .order_by(conversations.c.updated_at.desc())
            .limit(100)
        )
        rows = result.fetchall()

    return [
        {
            "id": r.id,
            "title": r.title,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    _require_db()
    async with database.SessionLocal() as session:
        conv_result = await session.execute(
            select(conversations).where(conversations.c.id == conversation_id)
        )
        conv = conv_result.fetchone()

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.user_id != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Forbidden")

        msg_result = await session.execute(
            select(messages)
            .where(messages.c.conversation_id == conversation_id)
            .order_by(messages.c.created_at.asc())
        )
        msgs = msg_result.fetchall()

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "messages": [
            {
                "role": m.role,
                "content": m.content or "",
                "citations": m.citations or [],
                "live_resources": m.live_resources or [],
                "emergency": m.emergency or False,
                "resources": m.resources or [],
            }
            for m in msgs
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    _require_db()
    async with database.SessionLocal() as session:
        conv_result = await session.execute(
            select(conversations.c.user_id).where(
                conversations.c.id == conversation_id
            )
        )
        conv = conv_result.fetchone()

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.user_id != current_user["sub"]:
            raise HTTPException(status_code=403, detail="Forbidden")

        await session.execute(
            delete(conversations).where(conversations.c.id == conversation_id)
        )
        await session.commit()
