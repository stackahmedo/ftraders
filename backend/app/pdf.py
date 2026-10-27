"""Server-side PDFs: A4 and 80 mm thermal receipt, with a verification QR code.

Printed documents use English text and "Tk" for the currency, because the built-in
PDF fonts cannot shape Bangla script. (Bangla PDFs need a Bengali TTF plus HarfBuzz
shaping; planned for a later phase.)
"""
from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import PUBLIC_BASE_URL
from .money import fmt_qty, fmt_taka
from .timeutil import to_local

if TYPE_CHECKING:  # keeps this module importable without SQLAlchemy
    from .models import Document

TITLES = {"estimate": "ESTIMATE / QUOTATION", "delivery": "DELIVERY CHALLAN", "invoice": "INVOICE / RECEIPT"}


def tk(paisa: int) -> str:
    return fmt_taka(paisa, symbol="Tk ")


def verify_url(doc: Document) -> str:
    return f"{PUBLIC_BASE_URL}/verify/{doc.verify_token}"


def _qr(url: str, size: float) -> Drawing:
    w = QrCodeWidget(url)
    x1, y1, x2, y2 = w.getBounds()
    d = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    d.add(w)
    return d


def _when(doc: Document) -> str:
    return to_local(doc.created_at).strftime("%d %b %Y, %I:%M %p")


def _safe(text: str | None) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_document_pdf(doc: Document, settings: dict[str, str], layout: str = "a4") -> bytes:
    return _thermal(doc, settings) if layout == "thermal" else _a4(doc, settings)


# ------------------------------------------------------------------ A4
def _a4(doc: Document, s: dict[str, str]) -> bytes:
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"{doc.number}", author=s.get("business_name", ""))
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=base, fontSize=8, leading=10, textColor=colors.HexColor("#444444"))
    h1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22)
    right = ParagraphStyle("right", parent=base, alignment=2)
    title_style = ParagraphStyle("title", parent=right, fontName="Helvetica-Bold", fontSize=13, leading=16)
    show_prices = doc.doc_type != "delivery"
    story = []

    contact = " | ".join(x for x in (f"Phone: {s.get('phone')}", f"Mobile: {s.get('mobile')}") if x)
    web = " | ".join(x for x in (s.get("email"), s.get("website")) if x)
    left = [Paragraph(_safe(s.get("business_name")), h1), Paragraph(_safe(s.get("address")), base),
            Paragraph(_safe(contact), base), Paragraph(_safe(web), base)]
    status_line = doc.status.upper()
    if doc.doc_type == "invoice" and doc.status != "void" and doc.payment_status:
        status_line = doc.payment_status.upper()
    right_col = [Paragraph(TITLES[doc.doc_type], title_style),
                 Paragraph(f"<b>No:</b> {doc.number}", right),
                 Paragraph(f"<b>Date:</b> {_when(doc)}", right),
                 Paragraph(f"<b>Status:</b> {status_line}", right)]
    if doc.parent:
        right_col.append(Paragraph(f"<b>Ref:</b> {doc.parent.number}", right))
    header = Table([[left, right_col]], colWidths=[105 * mm, 75 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [header, Spacer(1, 5 * mm)]

    bill = [Paragraph("<b>Bill to</b>" if doc.doc_type == "invoice" else "<b>Customer</b>", base),
            Paragraph(_safe(doc.customer_name), base)]
    if doc.customer_phone:
        bill.append(Paragraph(_safe(doc.customer_phone), base))
    if doc.customer_address:
        bill.append(Paragraph(_safe(doc.customer_address), base))
    story += [Table([[bill]], colWidths=[180 * mm]), Spacer(1, 4 * mm)]

    if show_prices:
        rows = [["#", "Item", "Qty", "Unit", "Rate", "Discount", "Amount"]]
        for i in doc.items:
            rows.append([str(i.line_no), Paragraph(_safe(i.description), base), fmt_qty(i.qty_milli), i.unit,
                         tk(i.unit_price_paisa), tk(i.discount_paisa) if i.discount_paisa else "-",
                         tk(i.line_total_paisa)])
        widths = [8 * mm, 72 * mm, 16 * mm, 14 * mm, 24 * mm, 20 * mm, 26 * mm]
    else:
        rows = [["#", "Item", "Qty", "Unit", "Received (tick)"]]
        for i in doc.items:
            rows.append([str(i.line_no), Paragraph(_safe(i.description), base), fmt_qty(i.qty_milli), i.unit, ""])
        widths = [8 * mm, 112 * mm, 20 * mm, 16 * mm, 24 * mm]
    items = Table(rows, colWidths=widths, repeatRows=1)
    items.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [items, Spacer(1, 4 * mm)]

    totals = []
    if show_prices:
        totals = [["Subtotal", tk(doc.subtotal_paisa)]]
        if doc.discount_paisa:
            totals.append(["Discount", "- " + tk(doc.discount_paisa)])
        totals.append(["Total", tk(doc.total_paisa)])
        if doc.doc_type == "invoice":
            totals += [["Paid", tk(doc.paid_paisa)], ["Due", tk(doc.due_paisa)]]
    qr = _qr(verify_url(doc), 28 * mm)
    maker = [Paragraph(f"Prepared by: <b>{_safe(doc.created_by.full_name)}</b>", small),
             Paragraph(f"Created: {_when(doc)}", small),
             Paragraph("Scan the QR code to verify this document.", small)]
    if doc.notes:
        maker.insert(0, Paragraph(f"<b>Notes:</b> {_safe(doc.notes)}", base))
    tot_table = Table(totals or [[""]], colWidths=[28 * mm, 32 * mm])
    tot_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 10),
        ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.black),
    ]))
    bottom = Table([[qr, maker, tot_table]], colWidths=[32 * mm, 88 * mm, 60 * mm])
    bottom.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [bottom, Spacer(1, 16 * mm)]

    sign = Table([["______________________", "", "______________________"],
                  ["Customer signature", "", "Authorised signature"]],
                 colWidths=[60 * mm, 60 * mm, 60 * mm])
    sign.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 9), ("ALIGN", (2, 0), (2, -1), "RIGHT")]))
    story += [sign, Spacer(1, 4 * mm), Paragraph(_safe(s.get("receipt_footer")), small)]

    def watermark(c: canvas.Canvas, _):
        if doc.status == "void":
            c.saveState()
            c.setFont("Helvetica-Bold", 90)
            c.setFillColor(colors.Color(0.85, 0, 0, alpha=0.25))
            c.translate(A4[0] / 2, A4[1] / 2)
            c.rotate(35)
            c.drawCentredString(0, 0, "VOID")
            c.setFont("Helvetica", 12)
            c.drawCentredString(0, -24, f"Reason: {(doc.void_reason or '')[:80]}")
            c.restoreState()

    pdf.build(story, onFirstPage=watermark, onLaterPages=watermark)
    return buf.getvalue()


# ------------------------------------------------------------------ 80 mm thermal
def _wrap(c: canvas.Canvas, text: str, font: str, size: float, width: float) -> list[str]:
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if c.stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            while c.stringWidth(w, font, size) > width and len(w) > 1:  # very long word
                cut = len(w)
                while cut > 1 and c.stringWidth(w[:cut], font, size) > width:
                    cut -= 1
                lines.append(w[:cut])
                w = w[cut:]
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _thermal(doc: Document, s: dict[str, str]) -> bytes:
    width = 80 * mm
    margin = 4 * mm
    inner = width - 2 * margin
    show_prices = doc.doc_type != "delivery"
    measure = canvas.Canvas(BytesIO())

    # Build a list of drawing ops first so the page height fits the content exactly.
    ops: list[tuple] = []  # (kind, payload, font, size, height)

    def text(t, font="Helvetica", size=8, align="left", gap=1.2):
        for line in _wrap(measure, t, font, size, inner):
            ops.append(("text", (line, align), font, size, size * gap + 1))

    def row(left, right_, font="Helvetica", size=8):
        ops.append(("row", (left, right_), font, size, size * 1.2 + 1))

    def rule():
        ops.append(("rule", None, None, None, 4))

    text(s.get("business_name", ""), "Helvetica-Bold", 12, "center")
    for line in (s.get("address"), f"Ph: {s.get('phone')}  Mob: {s.get('mobile')}", s.get("email"), s.get("website")):
        if line:
            text(line, size=7, align="center")
    rule()
    text(TITLES[doc.doc_type], "Helvetica-Bold", 9, "center")
    row(f"No: {doc.number}", _when(doc), size=7)
    text(f"Customer: {doc.customer_name}" + (f"  {doc.customer_phone}" if doc.customer_phone else ""), size=7)
    if doc.status == "void":
        text(f"*** VOID *** {doc.void_reason or ''}", "Helvetica-Bold", 8, "center")
    rule()
    for i in doc.items:
        text(f"{i.line_no}. {i.description}", size=8)
        if show_prices:
            disc = f" -{tk(i.discount_paisa)}" if i.discount_paisa else ""
            row(f"   {fmt_qty(i.qty_milli)} {i.unit} x {tk(i.unit_price_paisa)}{disc}", tk(i.line_total_paisa))
        else:
            row("   Qty", f"{fmt_qty(i.qty_milli)} {i.unit}")
    rule()
    if show_prices:
        row("Subtotal", tk(doc.subtotal_paisa))
        if doc.discount_paisa:
            row("Discount", "-" + tk(doc.discount_paisa))
        row("TOTAL", tk(doc.total_paisa), "Helvetica-Bold", 10)
        if doc.doc_type == "invoice":
            row("Paid", tk(doc.paid_paisa))
            row("Due", tk(doc.due_paisa), "Helvetica-Bold", 9)
            if doc.payment_status and doc.status != "void":
                text(f"Status: {doc.payment_status.upper()}", size=7, align="right")
        rule()
    text(f"Prepared by: {doc.created_by.full_name}", size=7)
    text(f"Time: {_when(doc)}", size=7)
    qr_size = 30 * mm
    ops.append(("qr", None, None, None, qr_size + 2 * mm))
    text("Scan to verify", size=6, align="center")
    if s.get("receipt_footer"):
        text(s["receipt_footer"], size=7, align="center")

    height = sum(op[4] for op in ops) + 2 * margin
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setTitle(doc.number)
    y = height - margin
    for kind, payload, font, size, h in ops:
        if kind == "text":
            line, align = payload
            c.setFont(font, size)
            base_y = y - size
            if align == "center":
                c.drawCentredString(width / 2, base_y, line)
            elif align == "right":
                c.drawRightString(width - margin, base_y, line)
            else:
                c.drawString(margin, base_y, line)
        elif kind == "row":
            left, right_ = payload
            c.setFont(font, size)
            c.drawString(margin, y - size, left)
            c.drawRightString(width - margin, y - size, right_)
        elif kind == "rule":
            c.setDash(1, 2)
            c.line(margin, y - 2, width - margin, y - 2)
            c.setDash()
        elif kind == "qr":
            renderPDF.draw(_qr(verify_url(doc), qr_size), c, (width - qr_size) / 2, y - qr_size - 1 * mm)
        y -= h
    c.showPage()
    c.save()
    return buf.getvalue()
