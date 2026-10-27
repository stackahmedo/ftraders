from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import AuditLog, User
from ..security import require
from ..services import settings as settings_svc

router = APIRouter(prefix="/api", tags=["settings & audit"])


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), _: User = Depends(require("settings.read"))):
    return settings_svc.get_all(db)


@router.put("/settings")
def put_settings(changes: dict[str, str] = Body(...), db: Session = Depends(get_db),
                 user: User = Depends(require("settings.write"))):
    result = settings_svc.update(db, user, changes)
    db.commit()
    return result


@router.get("/audit", response_model=list[schemas.AuditOut])
def audit_log(entity: str | None = None, entity_id: int | None = None, limit: int = 200,
              db: Session = Depends(get_db), _: User = Depends(require("audit.read"))):
    q = select(AuditLog).order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(min(limit, 2000))
    if entity:
        q = q.where(AuditLog.entity == entity)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    out = []
    for a in db.scalars(q):
        row = schemas.AuditOut.model_validate(a)
        row.user_name = a.user.full_name if a.user else None
        out.append(row)
    return out
