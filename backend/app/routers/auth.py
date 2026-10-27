from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..errors import BusinessError, NotFound
from ..models import Role, User
from ..security import create_access_token, get_current_user, hash_password, require, verify_password
from ..services import audit
from .serializers import user_out

router = APIRouter(prefix="/api", tags=["auth & users"])


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return schemas.TokenOut(access_token=create_access_token(user), user=user_out(user))


@router.get("/auth/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(role: str | None = None, db: Session = Depends(get_db),
               _: User = Depends(require("users.read", "docs.write"))):
    q = select(User).order_by(User.full_name)
    if role:
        q = q.join(Role).where(Role.name == role)
    return [user_out(u) for u in db.scalars(q)]


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserCreate, db: Session = Depends(get_db),
                actor: User = Depends(require("users.write"))):
    if db.scalar(select(User).where(User.username == body.username)):
        raise BusinessError("Username already taken")
    role = db.scalar(select(Role).where(Role.name == body.role))
    u = User(username=body.username, full_name=body.full_name, phone=body.phone,
             password_hash=hash_password(body.password), role_id=role.id)
    db.add(u)
    db.flush()
    audit.log(db, actor, "user", u.id, "create", "role", None, body.role)
    db.commit()
    return user_out(u)


@router.patch("/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, body: schemas.UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(require("users.write"))):
    u = db.get(User, user_id)
    if not u:
        raise NotFound("User")
    if u.id == actor.id and (body.is_active is False or (body.role and body.role != "owner")):
        raise BusinessError("You cannot deactivate or demote yourself")
    if body.full_name is not None:
        u.full_name = body.full_name
    if body.phone is not None:
        u.phone = body.phone
    if body.password:
        u.password_hash = hash_password(body.password)
        audit.log(db, actor, "user", u.id, "update", "password", None, "changed")
    if body.role and body.role != u.role_name:
        role = db.scalar(select(Role).where(Role.name == body.role))
        audit.log(db, actor, "user", u.id, "update", "role", u.role_name, body.role)
        u.role_id = role.id
    if body.is_active is not None and body.is_active != u.is_active:
        audit.log(db, actor, "user", u.id, "update", "is_active", u.is_active, body.is_active)
        u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    return user_out(u)
