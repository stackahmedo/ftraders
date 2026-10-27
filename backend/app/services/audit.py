from sqlalchemy.orm import Session

from ..models import AuditLog, User


def log(db: Session, user: User | None, entity: str, entity_id: int | None, action: str,
        field: str | None = None, old=None, new=None, reason: str | None = None) -> None:
    db.add(AuditLog(
        user_id=user.id if user else None, entity=entity, entity_id=entity_id, action=action,
        field=field,
        old_value=None if old is None else str(old),
        new_value=None if new is None else str(new),
        reason=reason,
    ))


def log_changes(db: Session, user: User, entity: str, obj, changes: dict, fields_to_log: set[str]) -> None:
    """Apply `changes` to `obj` and write one audit row per tracked field that changed."""
    for field, new in changes.items():
        old = getattr(obj, field)
        if old == new:
            continue
        setattr(obj, field, new)
        if field in fields_to_log:
            log(db, user, entity, obj.id, "update", field, old, new)
