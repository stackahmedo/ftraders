"""End-to-end through HTTP: permissions, approval prompt, PDF, QR verification."""
from .conftest import login
from .helpers import make


def sale_body(product, customer=None, qty="1", discount=0, pay=None, doc_type="invoice", **extra):
    body = {"doc_type": doc_type, "customer_id": customer.id if customer else None,
            "items": [{"product_id": product.id, "qty": qty, "discount_paisa": discount}]}
    if pay is not None:
        body["payment"] = {"amount_paisa": pay, "method": "cash"}
    body.update(extra)
    return body


def test_login_and_me(client, users):
    h = login(client, "cashier")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role_name"] == "cashier" and "docs.void" not in me["permissions"]
    assert client.get("/api/auth/me").status_code == 401


def test_role_permissions(client, users, product, retail):
    cashier, warehouse = login(client, "cashier"), login(client, "warehouse")
    r = client.post("/api/documents", json=sale_body(product, retail, pay=10000), headers=cashier)
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]
    assert client.post(f"/api/documents/{doc_id}/void", json={"reason": "test"}, headers=cashier).status_code == 403
    assert client.post("/api/documents", json=sale_body(product, retail, pay=10000), headers=warehouse).status_code == 403
    assert client.get("/api/settings", headers=cashier).status_code == 200
    assert client.put("/api/settings", json={"allow_negative_stock": "true"}, headers=cashier).status_code == 403
    r = client.post("/api/stock/movements", headers=warehouse,
                    json={"product_id": product.id, "qty": "5", "type": "stock_in"})
    assert r.status_code == 201
    assert client.post("/api/users", headers=login(client, "manager"),
                       json={"username": "x1", "full_name": "X", "password": "secret1", "role": "cashier"}
                       ).status_code == 403


def test_delivery_sees_only_own_challans(client, db, users, product, wholesale):
    mine = make(db, users["manager"], product, customer=wholesale, qty="1", doc_type="delivery",
                assigned_to_id=users["delivery"].id)
    other = make(db, users["manager"], product, customer=wholesale, qty="1", doc_type="delivery")
    h = login(client, "delivery")
    listed = [d["id"] for d in client.get("/api/documents", headers=h).json()]
    assert listed == [mine.id]
    assert client.get(f"/api/documents/{other.id}", headers=h).status_code == 404
    assert client.get(f"/api/documents/{mine.id}/pdf?layout=thermal", headers=h).status_code == 200


def test_discount_approval_round_trip(client, users, product, retail):
    h = login(client, "cashier")
    body = sale_body(product, retail, discount=2000, pay=8000)  # 20% off Tk 100
    r = client.post("/api/documents", json=body, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "approval_required" and r.json()["kind"] == "discount"
    body["discount_approval"] = {"username": "manager", "password": "wrong"}
    assert client.post("/api/documents", json=body, headers=h).status_code == 403
    body["discount_approval"] = {"username": "manager", "password": "manager123"}
    r = client.post("/api/documents", json=body, headers=h)
    assert r.status_code == 201 and r.json()["approved_by_name"] == "Manager"


def test_pdf_and_public_verify(client, users, product, wholesale):
    h = login(client, "cashier")
    r = client.post("/api/documents", json=sale_body(product, wholesale, qty="2", pay=13000), headers=h)
    assert r.status_code == 201, r.text
    doc = r.json()
    for layout in ("a4", "thermal"):
        r = client.get(f"/api/documents/{doc['id']}/pdf?layout={layout}", headers=h)
        assert r.status_code == 200 and r.content.startswith(b"%PDF")
    v = client.get(f"/api/public/verify/{doc['verify_token']}").json()
    assert v["number"] == doc["number"] and v["due_paisa"] == 5000
    assert client.get("/api/public/verify/nope").status_code == 404


def test_dashboard_and_dues(client, users, product, retail, wholesale):
    h = login(client, "manager")
    client.post("/api/documents", json=sale_body(product, retail, pay=10000), headers=h)
    client.post("/api/documents", json=sale_body(product, wholesale, qty="2"), headers=h)
    d = client.get("/api/dashboard", headers=h).json()
    assert d["sales_count"] == 2 and d["sales_paisa"] == 10000 + 18000 and d["collected_paisa"] == 10000
    dues = client.get("/api/dues", headers=h).json()
    assert dues["total_due_paisa"] == 18000 and dues["customers"][0]["customer_id"] == wholesale.id


def test_price_change_is_audited(client, users, product):
    h = login(client, "manager")
    p = client.get(f"/api/products/{product.id}", headers=h).json()
    body = {k: p[k] for k in ("name", "name_bn", "sku", "barcode", "unit", "buy_price_paisa",
                              "wholesale_price_paisa", "is_active")}
    body.update(retail_price_paisa=11000, low_stock="3", category=None)
    assert client.put(f"/api/products/{product.id}", json=body, headers=h).status_code == 200
    log = client.get("/api/audit?entity=product", headers=h).json()
    assert log[0]["field"] == "retail_price_paisa" and log[0]["old_value"] == "৳100.00"
    assert log[0]["new_value"] == "৳110.00" and log[0]["user_name"] == "Manager"
