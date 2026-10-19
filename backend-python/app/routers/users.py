"""API users - đăng ký/đăng nhập, ghi đồng thời 2 CSDL (saga/outbox)."""
import hashlib
import os

from fastapi import APIRouter, HTTPException

from ..models import UserCreate, LoginRequest
from ..services import sync
from .. import database as dbx

router = APIRouter(prefix="/users", tags=["users"])


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + "$" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
    return dk.hex() == dk_hex


@router.post("")
def create_user(body: UserCreate, strong: bool = False):
    """strong=true: nhất quán mạnh (rollback nếu Neo4j lỗi); mặc định dùng outbox."""
    if dbx.db.users.find_one({"username": body.username}):
        raise HTTPException(409, "Username đã tồn tại")
    try:
        return sync.create_user_dual_write(
            body.username, body.full_name, body.avatar_url,
            password_hash=hash_password(body.password), use_outbox=not strong,
        )
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/login")
def login(body: LoginRequest):
    u = dbx.db.users.find_one({"username": body.username})
    if not u or not verify_password(body.password, u.get("password_hash", "")):
        raise HTTPException(401, "Sai username hoặc mật khẩu")
    u.pop("password_hash", None)
    return u


@router.get("")
def list_users(limit: int = 50):
    return list(dbx.db.users.find({}, {"password_hash": 0}).limit(limit))


@router.get("/{user_id}")
def get_user(user_id: str):
    u = dbx.db.users.find_one({"_id": user_id}, {"password_hash": 0})
    if not u:
        raise HTTPException(404, "Không tìm thấy user")
    return u
