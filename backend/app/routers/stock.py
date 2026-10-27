from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import StockMovement, User
from ..money import qty_to_milli
from ..security import require
from ..services import stock as stock_svc
from .serializers import movement_out

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/movements", response_model=list[schemas.MovementOut])
def movements(product_id: int | None = None, type: str | None = None, limit: int = 200,
              db: Session = Depends(get_db), _: User = Depends(require("stock.read"))):
    q = select(StockMovement).order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(min(limit, 2000))
    if product_id:
        q = q.where(StockMovement.product_id == product_id)
    if type:
        q = q.where(StockMovement.type == type)
    return [movement_out(m) for m in db.scalars(q)]


@router.post("/movements", response_model=schemas.MovementOut, status_code=201)
def add_movement(body: schemas.MovementIn, db: Session = Depends(get_db),
                 user: User = Depends(require("stock.write"))):
    m = stock_svc.manual_movement(db, user, body.product_id, qty_to_milli(body.qty), body.type,
                                  body.reason, body.reference)
    db.commit()
    db.refresh(m)
    return movement_out(m)


@router.get("/low", response_model=list[schemas.LowStockOut])
def low_stock(db: Session = Depends(get_db), _: User = Depends(require("stock.read", "dashboard.read"))):
    return stock_svc.low_stock(db)
