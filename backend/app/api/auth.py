"""
Auth endpoints: register, login, me.
"""
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import insert, select, update

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app import database
from app.models.db import users

router = APIRouter()


def _require_db():
    if database.SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not configured")


class RegisterRequest(BaseModel):
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest):
    _require_db()
    async with database.SessionLocal() as session:
        result = await session.execute(
            select(users).where(users.c.email == body.email)
        )
        if result.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(uuid.uuid4())
        await session.execute(
            insert(users).values(
                id=user_id,
                email=body.email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                full_name="",
                clinic=None,
                country=None,
            )
        )
        await session.commit()

    token = create_access_token(user_id, body.email)
    return {
        "user_id": user_id,
        "email": body.email,
        "full_name": "",
        "token": token,
    }


@router.post("/login")
async def login(body: LoginRequest):
    _require_db()
    async with database.SessionLocal() as session:
        result = await session.execute(
            select(users).where(users.c.email == body.email)
        )
        row = result.fetchone()

    if not row or not verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(row.id), row.email)
    return {
        "user_id": str(row.id),
        "email": row.email,
        "full_name": row.full_name,
        "token": token,
    }


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    clinic: str | None = None
    country: str | None = None


@router.patch("/profile")
async def update_profile(body: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    _require_db()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    async with database.SessionLocal() as session:
        if updates:
            await session.execute(
                update(users).where(users.c.id == current_user["sub"]).values(**updates)
            )
            await session.commit()
        result = await session.execute(
            select(users).where(users.c.id == current_user["sub"])
        )
        row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(row.id),
        "email": row.email,
        "full_name": row.full_name,
        "clinic": row.clinic,
        "country": row.country,
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    _require_db()
    async with database.SessionLocal() as session:
        result = await session.execute(
            select(users).where(users.c.id == current_user["sub"])
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(row.id),
        "email": row.email,
        "full_name": row.full_name,
        "clinic": row.clinic,
        "country": row.country,
    }
