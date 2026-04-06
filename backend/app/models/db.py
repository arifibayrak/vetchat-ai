"""
SQLAlchemy Core table definitions.
Imported by database.py (metadata) and API modules.
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
)
from sqlalchemy.sql import func

from app.database import metadata

users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("full_name", String(255), nullable=False),
    Column("clinic", String(255), nullable=True),
    Column("country", String(100), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", String, primary_key=True),
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("title", String(60), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now()),
    Index("ix_conversations_user_id", "user_id"),
)

messages = Table(
    "messages",
    metadata,
    Column("id", String, primary_key=True),
    Column(
        "conversation_id",
        String,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String(20), nullable=False),
    Column("content", Text, nullable=True),
    Column("citations", JSON, nullable=True),
    Column("live_resources", JSON, nullable=True),
    Column("emergency", Boolean, default=False),
    Column("resources", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Index("ix_messages_conversation_id", "conversation_id"),
)
