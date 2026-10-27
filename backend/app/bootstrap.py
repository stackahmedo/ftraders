"""Reference data every database needs: roles, default settings, a first Owner."""
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ROLES, Role, User
from .security import hash_password
from .services import settings as settings_svc

ROLE_LABELS = {"owner": "Owner", "manager": "Manager", "cashier": "Cashier",
               "warehouse": "Warehouse", "delivery": "Delivery"}


def ensure_reference_data(db: Session) -> None:
    existing = set(db.scalars(select(Role.name)))
    for name in ROLES:
        if name not in existing:
            db.add(Role(name=name, label=ROLE_LABELS[name]))
    db.flush()
    settings_svc.ensure_defaults(db)
    if db.scalar(select(func.count(User.id))) == 0:
        owner_role = db.scalar(select(Role).where(Role.name == "owner"))
        db.add(User(username=os.environ.get("OWNER_USERNAME", "owner"), full_name="Owner",
                    password_hash=hash_password(os.environ.get("OWNER_PASSWORD", "owner123")),
                    role_id=owner_role.id))
    db.flush()
