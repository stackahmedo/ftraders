from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..errors import BusinessError, NotFound
from ..models import Category, Product, User
from ..money import fmt_taka, qty_to_milli
from ..security import require
from ..services import audit, stock
from .serializers import product_out

router = APIRouter(prefix="/api", tags=["products"])

PRICE_FIELDS = {"buy_price_paisa", "retail_price_paisa", "wholesale_price_paisa"}


def _category_id(db: Session, name: str | None) -> int | None:
    if not name or not name.strip():
        return None
    name = name.strip()
    cat = db.scalar(select(Category).where(Category.name == name))
    if not cat:
        cat = Category(name=name)
        db.add(cat)
        db.flush()
    return cat.id


def _check_unique(db: Session, body: schemas.ProductIn, exclude_id: int | None = None) -> None:
    conds = [Product.sku == body.sku]
    if body.barcode:
        conds.append(Product.barcode == body.barcode)
    q = select(Product).where(or_(*conds))
    if exclude_id:
        q = q.where(Product.id != exclude_id)
    if db.scalar(q):
        raise BusinessError("Another product already uses this SKU or barcode")


@router.get("/categories", response_model=list[schemas.CategoryOut])
def categories(db: Session = Depends(get_db), _: User = Depends(require("products.read"))):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(q: str | None = None, active_only: bool = True, limit: int = 500,
                  db: Session = Depends(get_db), _: User = Depends(require("products.read"))):
    query = select(Product).order_by(Product.name).limit(min(limit, 2000))
    if active_only:
        query = query.where(Product.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Product.name.ilike(like), Product.name_bn.ilike(like),
                                Product.sku.ilike(like), Product.barcode == q.strip()))
    products = db.scalars(query).all()
    levels = stock.stock_map(db, [p.id for p in products])
    return [product_out(p, levels.get(p.id, 0)) for p in products]


@router.get("/products/lookup/{code}", response_model=schemas.ProductOut)
def lookup(code: str, db: Session = Depends(get_db), _: User = Depends(require("products.read"))):
    """Barcode scanner / exact SKU lookup for the New Sale screen."""
    p = db.scalar(select(Product).where(or_(Product.barcode == code, Product.sku == code),
                                        Product.is_active.is_(True)))
    if not p:
        raise NotFound("Product")
    return product_out(p, stock.stock_of(db, p.id))


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(require("products.read"))):
    p = db.get(Product, product_id)
    if not p:
        raise NotFound("Product")
    return product_out(p, stock.stock_of(db, p.id))


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(body: schemas.ProductIn, db: Session = Depends(get_db),
                   user: User = Depends(require("products.write"))):
    _check_unique(db, body)
    p = Product(name=body.name, name_bn=body.name_bn, sku=body.sku, barcode=body.barcode,
                category_id=_category_id(db, body.category), unit=body.unit,
                buy_price_paisa=body.buy_price_paisa, retail_price_paisa=body.retail_price_paisa,
                wholesale_price_paisa=body.wholesale_price_paisa,
                low_stock_milli=qty_to_milli(body.low_stock), is_active=body.is_active)
    db.add(p)
    db.flush()
    audit.log(db, user, "product", p.id, "create", None, None, f"{p.sku} {p.name}")
    db.commit()
    return product_out(p)


@router.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, body: schemas.ProductIn, db: Session = Depends(get_db),
                   user: User = Depends(require("products.write"))):
    p = db.get(Product, product_id)
    if not p:
        raise NotFound("Product")
    _check_unique(db, body, exclude_id=p.id)
    changes = {
        "name": body.name, "name_bn": body.name_bn, "sku": body.sku, "barcode": body.barcode,
        "category_id": _category_id(db, body.category), "unit": body.unit,
        "buy_price_paisa": body.buy_price_paisa, "retail_price_paisa": body.retail_price_paisa,
        "wholesale_price_paisa": body.wholesale_price_paisa,
        "low_stock_milli": qty_to_milli(body.low_stock), "is_active": body.is_active,
    }
    for field, new in changes.items():
        old = getattr(p, field)
        if old != new:
            if field in PRICE_FIELDS:
                audit.log(db, user, "product", p.id, "update", field, fmt_taka(old), fmt_taka(new))
            elif field in ("sku", "barcode", "is_active", "unit"):
                audit.log(db, user, "product", p.id, "update", field, old, new)
            setattr(p, field, new)
    db.commit()
    db.refresh(p)
    return product_out(p, stock.stock_of(db, p.id))
