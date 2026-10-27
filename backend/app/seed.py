"""Demo data: users for every role, 10 products with opening stock, 5 customers of each type,
and a few sample documents.  Run after migrations:   python -m app.seed
Safe to run twice: it skips anything that already exists.
"""
from sqlalchemy import select

from .bootstrap import ensure_reference_data
from .db import SessionLocal
from .models import Category, Customer, Document, Product, Role, User
from .money import qty_to_milli, taka_to_paisa
from .security import hash_password
from .services import documents as doc_svc
from .services import payments as pay_svc
from .services import stock as stock_svc
from .timeutil import local_today

USERS = [  # username, full name, role, password
    ("owner", "Fazlur Rahman", "owner", "owner123"),
    ("manager", "Karim Uddin", "manager", "manager123"),
    ("cashier", "Rina Akter", "cashier", "cashier123"),
    ("warehouse", "Jamal Hossain", "warehouse", "warehouse123"),
    ("delivery", "Sohel Mia", "delivery", "delivery123"),
]

PRODUCTS = [  # sku, barcode, name, name_bn, category, unit, buy, retail, wholesale, low, opening
    ("RICE-MIN", "8941100000011", "Miniket Rice", "মিনিকেট চাল", "Rice", "kg", "62", "72", "68", "100", "500"),
    ("DAL-MSR", "8941100000028", "Masoor Dal", "মসুর ডাল", "Pulses", "kg", "98", "115", "108", "50", "200"),
    ("OIL-SOY5", "8941100000035", "Soybean Oil 5L", "সয়াবিন তেল ৫ লিটার", "Oil", "piece", "780", "850", "820", "20", "60"),
    ("SUGAR", "8941100000042", "Sugar", "চিনি", "Grocery", "kg", "118", "135", "128", "50", "150"),
    ("ATTA-2", "8941100000059", "Atta 2kg", "আটা ২ কেজি", "Flour", "piece", "105", "125", "118", "30", "80"),
    ("SALT-1", "8941100000066", "Iodized Salt 1kg", "আয়োডিনযুক্ত লবণ", "Grocery", "piece", "32", "42", "38", "40", "120"),
    ("TEA-400", "8941100000073", "Tea 400g", "চা পাতা ৪০০ গ্রাম", "Beverage", "piece", "190", "230", "215", "20", "45"),
    ("BISC-CTN", "8941100000080", "Biscuit Carton (24 pcs)", "বিস্কুট কার্টন", "Snacks", "carton", "420", "480", "455", "10", "8"),
    ("DET-1", "8941100000097", "Detergent Powder 1kg", "ডিটারজেন্ট পাউডার", "Household", "piece", "135", "160", "150", "25", "70"),
    ("SOAP-CTN", "8941100000103", "Bath Soap Carton (48 pcs)", "সাবান কার্টন", "Household", "carton", "1850", "2100", "1990", "5", "12"),
]

CUSTOMERS = {
    "retail": [("Abdul Karim", "01711000001", "Mirpur 10, Dhaka"),
               ("Nasrin Sultana", "01811000002", "Uttara Sector 7, Dhaka"),
               ("Mahmudul Hasan", "01911000003", "Mohammadpur, Dhaka"),
               ("Shirin Begum", "01611000004", "Dhanmondi 27, Dhaka"),
               ("Tanvir Ahmed", "01511000005", "Badda, Dhaka")],
    "wholesale": [("Bismillah Store", "01712000001", "Kawran Bazar, Dhaka"),
                  ("Madina Traders", "01812000002", "Moulvibazar, Dhaka"),
                  ("Al-Amin Enterprise", "01912000003", "Savar, Dhaka"),
                  ("Rahim General Store", "01612000004", "Gazipur Chowrasta"),
                  ("Shapla Super Shop", "01512000005", "Narayanganj")],
    "credit": [("Hasan Grocery", "01713000001", "Mirpur 1, Dhaka"),
               ("Mollah Stores", "01813000002", "Jatrabari, Dhaka"),
               ("Kashem Bhai Dokan", "01913000003", "Rampura, Dhaka"),
               ("Nur Islam Traders", "01613000004", "Keraniganj"),
               ("Sumi Variety Store", "01513000005", "Tongi, Gazipur")],
}
CREDIT_LIMITS = {"retail": "0", "wholesale": "50000", "credit": "30000"}


def run() -> None:
    db = SessionLocal()
    try:
        ensure_reference_data(db)
        roles = {r.name: r for r in db.scalars(select(Role))}
        users = {}
        for username, full_name, role, password in USERS:
            u = db.scalar(select(User).where(User.username == username))
            if not u:
                u = User(username=username, full_name=full_name, password_hash=hash_password(password),
                         role_id=roles[role].id)
                db.add(u)
            elif username == "owner" and u.full_name == "Owner":
                u.full_name = full_name
            users[username] = u
        db.flush()
        owner = users["owner"]

        for sku, barcode, name, name_bn, cat, unit, buy, retail, wholesale, low, opening in PRODUCTS:
            if db.scalar(select(Product).where(Product.sku == sku)):
                continue
            c = db.scalar(select(Category).where(Category.name == cat))
            if not c:
                c = Category(name=cat)
                db.add(c)
                db.flush()
            p = Product(sku=sku, barcode=barcode, name=name, name_bn=name_bn, category_id=c.id, unit=unit,
                        buy_price_paisa=taka_to_paisa(buy), retail_price_paisa=taka_to_paisa(retail),
                        wholesale_price_paisa=taka_to_paisa(wholesale), low_stock_milli=qty_to_milli(low))
            db.add(p)
            db.flush()
            stock_svc.add_movement(db, users["warehouse"], p.id, qty_to_milli(opening), "stock_in",
                                   reference="Opening stock")

        for ctype, rows in CUSTOMERS.items():
            for name, phone, address in rows:
                if db.scalar(select(Customer).where(Customer.phone == phone)):
                    continue
                db.add(Customer(name=name, phone=phone, address=address, type=ctype,
                                credit_limit_paisa=taka_to_paisa(CREDIT_LIMITS[ctype])))
        db.flush()

        if not db.scalar(select(Document.id).limit(1)):
            prod = {p.sku: p for p in db.scalars(select(Product))}
            cust = {c.name: c for c in db.scalars(select(Customer))}
            L = doc_svc.LineIn
            # Paid retail invoice
            doc_svc.create_document(db, users["cashier"], doc_type="invoice", customer_id=cust["Abdul Karim"].id,
                                    lines=[L(prod["RICE-MIN"].id, qty_to_milli("5")),
                                           L(prod["OIL-SOY5"].id, qty_to_milli("1"))],
                                    payment=doc_svc.PaymentIn(taka_to_paisa("1210"), "cash"))
            # Wholesale estimate -> delivery challan -> invoice with partial bKash payment
            est = doc_svc.create_document(db, users["manager"], doc_type="estimate",
                                          customer_id=cust["Bismillah Store"].id,
                                          lines=[L(prod["SUGAR"].id, qty_to_milli("20")),
                                                 L(prod["DAL-MSR"].id, qty_to_milli("10"), taka_to_paisa("50"))],
                                          notes="Weekly order")
            dlv = doc_svc.convert(db, users["manager"], est, "delivery", assigned_to_id=users["delivery"].id)
            doc_svc.convert(db, users["manager"], dlv, "invoice",
                            payment=doc_svc.PaymentIn(taka_to_paisa("2000"), "bkash", "TRX8XK2Q1"))
            # Credit sale on installments
            inv = doc_svc.create_document(db, owner, doc_type="invoice", customer_id=cust["Hasan Grocery"].id,
                                          lines=[L(prod["SOAP-CTN"].id, qty_to_milli("2")),
                                                 L(prod["DET-1"].id, qty_to_milli("10"))],
                                          payment=doc_svc.PaymentIn(taka_to_paisa("1000"), "nagad"))
            pay_svc.set_installment_plan(db, owner, inv, count=3, first_due=local_today(), interval_days=30)
        db.commit()
        print("Seed complete. Logins: " + ", ".join(f"{u}/{p}" for u, _, _, p in USERS))
    finally:
        db.close()


if __name__ == "__main__":
    run()
