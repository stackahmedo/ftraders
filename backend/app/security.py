"""Passwords, JWT and role permissions (enforced on every endpoint)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_MINUTES, SECRET_KEY
from .db import get_db
from .models import User

# ------------------------------------------------------------------ passwords
# PBKDF2-SHA256 from the standard library: no native build dependency.
_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iterations))
    return hmac.compare_digest(digest, base64.b64decode(digest_b64))


# ------------------------------------------------------------------ permissions
P = {
    "products.read", "products.write",
    "customers.read", "customers.write", "customers.credit",   # credit = limit / opening balance
    "stock.read", "stock.write",
    "docs.read", "docs.read_own", "docs.write", "docs.void",
    "payments.read", "payments.write", "payments.reverse",
    "dashboard.read", "settings.read", "settings.write",
    "users.read", "users.write", "audit.read",
    "approve.discount", "approve.credit",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": set(P),
    "manager": P - {"settings.write", "users.write", "approve.credit"},
    "cashier": {
        "products.read", "customers.read", "customers.write", "stock.read",
        "docs.read", "docs.write", "payments.read", "payments.write",
        "dashboard.read", "settings.read",
    },
    "warehouse": {"products.read", "stock.read", "stock.write", "dashboard.read", "settings.read"},
    "delivery": {"docs.read_own", "settings.read"},
}


def has_perm(user: User, perm: str) -> bool:
    return perm in ROLE_PERMISSIONS.get(user.role_name, set())


# ------------------------------------------------------------------ JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role_name, "iat": now,
               "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user


def require(*perms: str):
    """Dependency: the user must hold at least one of `perms`."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if not any(has_perm(user, p) for p in perms):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action")
        return user
    return checker


def verify_approver(db: Session, username: str | None, password: str | None, perm: str) -> User:
    """Check a supervisor's credentials typed in at the counter (e.g. for a big discount)."""
    if not username or not password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approval required")
    approver = db.scalar(select(User).where(User.username == username))
    if not approver or not approver.is_active or not verify_password(password, approver.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approval failed: wrong username or password")
    if not has_perm(approver, perm):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Approver does not have the required role")
    return approver
