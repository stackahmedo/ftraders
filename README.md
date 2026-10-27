# F Rahman Traders — ERP (Phase 1 MVP)

Web ERP for a retail + wholesale trading business: products, customers (buyer list), stock ledger,
estimates → delivery challans → invoices, payments with installments, due list, A4 and 80 mm
printouts with a verification QR code, roles, and a full audit trail. English / বাংলা UI, BDT (৳).

```
frahman-erp/
├── backend/                 FastAPI + SQLAlchemy 2 + Alembic
│   ├── app/
│   │   ├── main.py          app, error handlers, routers, serves frontend/dist in production
│   │   ├── models.py        all tables
│   │   ├── money.py         paisa / quantity maths (pure, no floats)
│   │   ├── security.py      PBKDF2 passwords, JWT, role → permission map
│   │   ├── services/        business rules: stock, documents, payments, settings, audit
│   │   ├── routers/         HTTP endpoints (permissions enforced here)
│   │   ├── pdf.py           A4 + 80 mm thermal PDFs with QR
│   │   ├── bootstrap.py     roles, default settings, first Owner
│   │   └── seed.py          demo data
│   ├── alembic/versions/0001_initial.py
│   └── tests/               pytest: stock ledger, payments, void, API permissions
└── frontend/                React 18 + TypeScript + Tailwind (Vite)
    └── src/pages/           Login, Dashboard, NewSale, Documents, DocumentDetail, Products,
                             Customers, CustomerLedger, Stock, Dues, Settings, Users, Audit, Verify
```

## Run it

Needs **Python 3.11+** and **Node 18+**.

### 1. Backend (terminal 1)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then change SECRET_KEY (Windows: copy .env.example .env)
alembic upgrade head          # creates erp.db (SQLite)
python -m app.seed            # optional demo data
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173  (also reachable from phones on the same Wi-Fi)
```

### 3. Log in

| Username  | Password     | Role      | Can do |
|-----------|--------------|-----------|--------|
| owner     | owner123     | Owner     | everything, settings, users, credit-limit approval |
| manager   | manager123   | Manager   | everything except settings/users; approves discounts; voids |
| cashier   | cashier123   | Cashier   | sales, payments, retail customers |
| warehouse | warehouse123 | Warehouse | stock in/out, adjustments, low stock |
| delivery  | delivery123  | Delivery  | only delivery challans assigned to them |

Without the seed, only `owner / owner123` exists (override with `OWNER_USERNAME` / `OWNER_PASSWORD`
in `.env` before first start). **Change all passwords before real use.**

### Tests

```bash
cd backend
pytest -q
```

### Production (one process)

```bash
cd frontend && npm run build          # creates frontend/dist
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```
FastAPI serves the built app and the API on the same port. Set `PUBLIC_BASE_URL` to the address
customers will reach (it goes into the QR code), and `CORS_ORIGINS` if the UI is on another origin.

### Move to PostgreSQL

```bash
pip install "psycopg[binary]"
# .env:  DATABASE_URL=postgresql+psycopg://user:pass@host/frahman
alembic upgrade head
```
Models use only portable types (BIGINT money, string enums, naive-UTC timestamps). Serial numbers and
stock checks take row locks (`SELECT … FOR UPDATE`), so concurrent cashiers are safe on PostgreSQL.

## Database design

```mermaid
erDiagram
    roles ||--o{ users : has
    categories ||--o{ products : groups
    customers ||--o{ documents : "buys on"
    users ||--o{ documents : "created_by / assigned_to / approved_by / voided_by"
    documents ||--o{ document_items : contains
    documents ||--o| documents : "parent (Estimate→Challan→Invoice)"
    products ||--o{ document_items : "sold as"
    products ||--o{ stock_movements : "ledger rows"
    documents ||--o{ stock_movements : "caused"
    stock_movements ||--o| stock_movements : "reversal_of"
    documents ||--o{ payments : "paid by"
    customers ||--o{ payments : "pays"
    payments ||--o| payments : "reversal_of"
    documents ||--o{ installments : "schedule"
    users ||--o{ audit_logs : "did"
```

| Table | Key columns |
|---|---|
| roles | name (owner/manager/cashier/warehouse/delivery) |
| users | username, full_name, password_hash, role_id, is_active |
| categories | name |
| products | name, name_bn, sku, barcode, category_id, unit, buy/retail/wholesale_price_paisa, low_stock_milli — **no stock column** |
| customers | name, phone, address, type (retail/wholesale/credit), credit_limit_paisa, opening_balance_paisa, notes |
| stock_movements | created_at, product_id, qty_milli (±), type, document_id, reversal_of_id, reason, reference, user_id |
| documents | doc_type, number, status, customer snapshot, price_tier, subtotal/discount/total/paid_paisa, payment_status, parent_id, moves_stock, verify_token, created_by/at, voided_by/at, void_reason |
| document_items | product_id, description, unit, qty_milli, unit_price_paisa, discount_paisa, line_total_paisa, buy_price_paisa (cost snapshot) |
| payments | customer_id, document_id, amount_paisa (negative = reversal), method, reference, paid_at, reversal_of_id, user_id |
| installments | document_id, seq, due_date, amount_paisa |
| audit_logs | at, user_id, entity, entity_id, action, field, old_value, new_value, reason |
| settings | key → value (business info, prefixes, counters, thresholds) |

## Business rules (where they live)

| Rule | Implementation |
|---|---|
| Stock is computed, never stored | `services/stock.py` — `SUM(qty_milli)` per product |
| Stock cannot go negative unless Owner allows | `stock.check_available`, setting `allow_negative_stock` (owner-only) |
| Estimate: nothing; Challan: stock out; Invoice: stock + money | `services/documents.py` `MOVES_STOCK` |
| Invoice made from a challan doesn't take stock twice | `moves_stock = False` when parent is a challan |
| One-click conversion copies lines and prices | `documents.convert` |
| Separate numbering EST/DLV/INV | `settings.next_number` (locked counter row; numbers never reused) |
| Customer type picks price tier; wholesale price only for wholesale | `documents.price_tier_for` — server decides the price, not the browser |
| Credit sale above limit needs the Owner | `documents._check_credit` → 409 `approval_required`; UI asks for Owner login |
| Discount above X% needs Manager/Owner | `documents._check_discount` (setting `discount_approval_percent`, default 10) |
| Void never deletes; reverses with new rows | `documents.void` → `void_reversal` stock rows + negative payment rows |
| Audit of prices, stock, payments, voids, settings, users | `services/audit.py`, called from services/routers |
| No floats for money | integer paisa everywhere; quantities in milli-units (kg sales) |

## Assumptions made

- Quantities allow 3 decimals (e.g. 0.250 kg); stored as integer milli-units.
- Discounts are entered per line as an amount (৳), not a percent.
- A walk-in sale (no customer chosen) must be paid in full; to sell on credit, pick a customer.
- Credit customers buy at retail price; only `wholesale` customers get the wholesale price.
- Retail customers have a ৳0 credit limit by default, so any due on them needs Owner approval.
- Supervisor approval is given by typing the Manager/Owner username + password on the cashier's screen.
- Voiding an invoice made from a challan keeps the goods "out" (they left with the challan) and re-opens
  the challan; void the challan too if the goods came back.
- Installment paid/unpaid marks are derived: payments after the plan fill installments in date order.
- A cashier can add retail customers only; wholesale/credit customers and credit limits need a Manager.
- Printed PDFs are in English with "Tk" because the built-in PDF fonts cannot shape Bangla script; the
  screen UI is fully bilingual. Bangla PDFs need a Bengali TTF + HarfBuzz shaping (planned).
- "Due collected today" = money received today against older invoices or on account (not the payment
  taken at the counter for an invoice made today).

## Ready for later phases

- **Phase 2** — `doc_type` / `movement type` are open strings: add `purchase_order`, `sales_return`,
  `purchase_return` and the `return` movement type already exists. Suppliers can mirror `customers`;
  the payments table can take a `supplier_id` for payables; expenses/cash book as new tables.
- **Phase 3** — `document_items.buy_price_paisa` is snapshotted at sale time for the profit report;
  stock value = ledger × buy price; due aging from `documents.created_at` + `installments`.
  WhatsApp: the public verify URL / PDF link can go into a `wa.me/880…?text=` link.
- **Phase 4** — challans already have `assigned_to_id` and the Delivery role; add a `deliveries` table
  (vehicle, route, status Packed → On the way → Delivered/Failed, cash collected).
