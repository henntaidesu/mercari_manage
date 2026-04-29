# -*- coding: utf-8 -*-
import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel as PydanticModel

from ..auth import create_access_token
from ..database import DatabaseManager

router = APIRouter(prefix="/api/auth", tags=["auth"])
db = DatabaseManager()


class LoginRequest(PydanticModel):
    username: str
    password: str


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return digest.hex()


def _ensure_default_admin():
    user_count = db.execute_query("SELECT COUNT(*) FROM [users]")
    if user_count and user_count[0][0] > 0:
        return
    salt_hex = secrets.token_hex(16)
    password_hash = _hash_password("admin", salt_hex)
    db.execute_insert(
        """
        INSERT INTO [users] (username, password_hash, salt, display_name, is_active)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("admin", password_hash, salt_hex, "系统管理员", 1),
    )


@router.on_event("startup")
def startup_seed_user():
    _ensure_default_admin()


@router.post("/login")
def login(data: LoginRequest):
    username = (data.username or "").strip()
    password = data.password or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    rows = db.execute_query(
        """
        SELECT id, username, password_hash, salt, display_name, is_active
        FROM [users]
        WHERE username = ?
        LIMIT 1
        """,
        (username,),
    )
    if not rows:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user_id, db_username, db_hash, db_salt, display_name, is_active = rows[0]
    if not is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    if _hash_password(password, db_salt) != db_hash:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    db.execute_update(
        "UPDATE [users] SET last_login_at = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
    )

    return {
        "token": create_access_token(user_id, db_username),
        "user": {
            "id": user_id,
            "username": db_username,
            "display_name": display_name or db_username,
        },
    }
