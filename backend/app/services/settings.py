from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import BusinessError
from ..models import Setting, User
from . import audit

DEFAULTS: dict[str, str] = {
    "business_name": "F Rahman Traders",
    "business_name_bn": "এফ রহমান ট্রেডার্স",
    "address": "[ADDRESS]",
    "phone": "[PHONE]",
    "mobile": "[MOBILE]",
    "email": "[EMAIL]",
    "website": "[WEBSITE]",
    "currency_symbol": "৳",
    "receipt_footer": "Thank you for your business!",
    "allow_negative_stock": "false",
    "discount_approval_percent": "10",
    "number_padding": "4",
    "prefix_estimate": "EST",
    "prefix_delivery": "DLV",
    "prefix_invoice": "INV",
    "next_estimate": "1",
    "next_delivery": "1",
    "next_invoice": "1",
}

BOOL_KEYS = {"allow_negative_stock"}
INT_KEYS = {"number_padding", "next_estimate", "next_delivery", "next_invoice"}


def ensure_defaults(db: Session) -> None:
    existing = set(db.scalars(select(Setting.key)))
    for key, value in DEFAULTS.items():
        if key not in existing:
            db.add(Setting(key=key, value=value))
    db.flush()


def get_all(db: Session) -> dict[str, str]:
    values = dict(DEFAULTS)
    values.update({s.key: s.value for s in db.scalars(select(Setting))})
    return values


def get(db: Session, key: str) -> str:
    row = db.get(Setting, key)
    return row.value if row else DEFAULTS.get(key, "")


def get_bool(db: Session, key: str) -> bool:
    return get(db, key).strip().lower() in ("1", "true", "yes", "on")


def update(db: Session, user: User, changes: dict[str, str]) -> dict[str, str]:
    for key, value in changes.items():
        if key not in DEFAULTS:
            raise BusinessError(f"Unknown setting: {key}")
        value = str(value).strip()
        if key in BOOL_KEYS:
            value = "true" if value.lower() in ("1", "true", "yes", "on") else "false"
        if key in INT_KEYS and (not value.isdigit() or int(value) < 1):
            raise BusinessError(f"{key} must be a positive whole number")
        if key == "discount_approval_percent":
            try:
                pct = Decimal(value)
            except InvalidOperation:
                pct = Decimal(-1)
            if not Decimal(0) <= pct <= Decimal(100):
                raise BusinessError("discount_approval_percent must be between 0 and 100")
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=DEFAULTS[key])
            db.add(row)
        if row.value != value:
            audit.log(db, user, "setting", None, "update", key, row.value, value)
            row.value = value
    db.flush()
    return get_all(db)


def next_number(db: Session, doc_type: str) -> str:
    """Take the next serial for a document type (EST-0001, DLV-0001, INV-0001).

    The counter row is locked (SELECT ... FOR UPDATE) so two cashiers on PostgreSQL
    never get the same number; SQLite serialises writers anyway.
    """
    key = f"next_{doc_type}"
    row = db.scalar(select(Setting).where(Setting.key == key).with_for_update())
    if row is None:
        row = Setting(key=key, value="1")
        db.add(row)
        db.flush()
    n = int(row.value)
    row.value = str(n + 1)
    pad = int(get(db, "number_padding") or 4)
    prefix = get(db, f"prefix_{doc_type}")
    return f"{prefix}-{n:0{pad}d}"
