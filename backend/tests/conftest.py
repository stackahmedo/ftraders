import os

os.environ["DATABASE_URL"] = "sqlite://"  # never touch a real database file from tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.bootstrap import ensure_reference_data
from app.db import Base, get_db
from app.main import app
from app.models import Customer, Product, Role, User
from app.money import qty_to_milli, taka_to_paisa
from app.security import hash_password
from app.services import stock


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(Session):
    s = Session()
    ensure_reference_data(s)
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def users(db):
    roles = {r.name: r for r in db.query(Role)}
    out = {"owner": db.query(User).filter_by(username="owner").one()}
    for name in ("manager", "cashier", "warehouse", "delivery"):
        u = User(username=name, full_name=name.title(), password_hash=hash_password(f"{name}123"),
                 role_id=roles[name].id)
        db.add(u)
        out[name] = u
    db.commit()
    return out


@pytest.fixture()
def product(db, users):
    """Retail Tk 100, wholesale Tk 90, opening stock 10."""
    p = Product(name="Test Rice", sku="T-RICE", barcode="111", unit="kg",
                buy_price_paisa=taka_to_paisa("80"), retail_price_paisa=taka_to_paisa("100"),
                wholesale_price_paisa=taka_to_paisa("90"), low_stock_milli=qty_to_milli("3"))
    db.add(p)
    db.flush()
    stock.add_movement(db, users["warehouse"], p.id, qty_to_milli("10"), "stock_in")
    db.commit()
    return p


def _customer(db, name, type_, limit="0"):
    c = Customer(name=name, phone=name[:3], type=type_, credit_limit_paisa=taka_to_paisa(limit))
    db.add(c)
    db.commit()
    return c


@pytest.fixture()
def retail(db):
    return _customer(db, "Retail Buyer", "retail")


@pytest.fixture()
def wholesale(db):
    return _customer(db, "Wholesale Buyer", "wholesale", "5000")


@pytest.fixture()
def credit(db):
    return _customer(db, "Credit Buyer", "credit", "500")


@pytest.fixture()
def client(Session, db):
    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def login(client, username, password=None):
    r = client.post("/api/auth/login", data={"username": username, "password": password or f"{username}123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
