from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..errors import BusinessError, NotFound
from ..models import Customer, User
from ..money import fmt_taka
from ..security import has_perm, require
from ..services import audit
from ..services import payments as pay_svc

router = APIRouter(prefix="/api/customers", tags=["customers"])

CREDIT_FIELDS = {"credit_limit_paisa", "opening_balance_paisa", "type"}


def _out(c: Customer, balance: int) -> schemas.CustomerOut:
    out = schemas.CustomerOut.model_validate(c)
    out.balance_paisa = balance
    return out


@router.get("", response_model=list[schemas.CustomerOut])
def list_customers(q: str | None = None, type: str | None = None, active_only: bool = True,
                   with_due: bool = False, limit: int = 500, db: Session = Depends(get_db),
                   _: User = Depends(require("customers.read"))):
    query = select(Customer).order_by(Customer.name).limit(min(limit, 2000))
    if active_only:
        query = query.where(Customer.is_active.is_(True))
    if type:
        query = query.where(Customer.type == type)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Customer.name.ilike(like), Customer.phone.ilike(like)))
    customers = db.scalars(query).all()
    balances = pay_svc.balances_for(db, [c.id for c in customers])
    result = [_out(c, balances.get(c.id, 0)) for c in customers]
    if with_due:
        result = sorted((c for c in result if c.balance_paisa > 0), key=lambda c: -c.balance_paisa)
    return result


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), _: User = Depends(require("customers.read"))):
    c = db.get(Customer, customer_id)
    if not c:
        raise NotFound("Customer")
    return _out(c, pay_svc.customer_balance(db, c.id))


@router.get("/{customer_id}/ledger", response_model=schemas.LedgerOut)
def ledger(customer_id: int, db: Session = Depends(get_db), _: User = Depends(require("customers.read"))):
    data = pay_svc.customer_ledger(db, customer_id)
    c = db.get(Customer, customer_id)
    return schemas.LedgerOut(customer=_out(c, data["balance_paisa"]),
                             opening_balance_paisa=data["opening_balance_paisa"],
                             balance_paisa=data["balance_paisa"],
                             entries=[schemas.LedgerEntry(**e) for e in data["entries"]])


@router.post("", response_model=schemas.CustomerOut, status_code=201)
def create_customer(body: schemas.CustomerIn, db: Session = Depends(get_db),
                    user: User = Depends(require("customers.write"))):
    if not has_perm(user, "customers.credit") and (
            body.credit_limit_paisa or body.opening_balance_paisa or body.type != "retail"):
        raise BusinessError("Only a Manager or Owner can add wholesale/credit customers or set credit amounts",
                            status_code=403)
    c = Customer(**body.model_dump())
    db.add(c)
    db.flush()
    audit.log(db, user, "customer", c.id, "create", None, None, f"{c.name} ({c.type})")
    if c.credit_limit_paisa:
        audit.log(db, user, "customer", c.id, "update", "credit_limit_paisa", None, fmt_taka(c.credit_limit_paisa))
    if c.opening_balance_paisa:
        audit.log(db, user, "customer", c.id, "update", "opening_balance_paisa", None,
                  fmt_taka(c.opening_balance_paisa))
    db.commit()
    return _out(c, pay_svc.customer_balance(db, c.id))


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, body: schemas.CustomerIn, db: Session = Depends(get_db),
                    user: User = Depends(require("customers.write"))):
    c = db.get(Customer, customer_id)
    if not c:
        raise NotFound("Customer")
    data = body.model_dump()
    if not has_perm(user, "customers.credit"):
        if any(data[f] != getattr(c, f) for f in CREDIT_FIELDS):
            raise BusinessError("Only a Manager or Owner can change type, credit limit or opening balance",
                                status_code=403)
    for field, new in data.items():
        old = getattr(c, field)
        if old == new:
            continue
        if field in CREDIT_FIELDS:
            shown_old, shown_new = (old, new) if field == "type" else (fmt_taka(old), fmt_taka(new))
            audit.log(db, user, "customer", c.id, "update", field, shown_old, shown_new)
        setattr(c, field, new)
    db.commit()
    return _out(c, pay_svc.customer_balance(db, c.id))
