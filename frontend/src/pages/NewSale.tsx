import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Card, ErrorText, Field, Input, PageHeader, Select, useApproval } from "../components/ui";
import { api, ApiError } from "../lib/api";
import { useApi, useDebounced } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import { fmtQty, lineGross, paisaToInput, toMilli, toPaisa } from "../lib/money";
import type { Customer, DocDetail, DocType, Product, User } from "../lib/types";

interface Row {
  product: Product;
  qty: string;
  discount: string; // taka
}

function CustomerPicker({ value, onChange }: { value: Customer | null; onChange: (c: Customer | null) => void }) {
  const { t, money } = useI18n();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const dq = useDebounced(q);
  const { data } = useApi<Customer[]>(open ? `/api/customers?limit=10&q=${encodeURIComponent(dq)}` : null);

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-slate-300 bg-white px-3 py-2">
        <div className="min-w-0 pr-2">
          <div className="truncate font-medium">{value.name} <Badge value={value.type} /></div>
          <div className="truncate text-xs text-slate-500">
            {value.phone} · {t("balance")}: {money(value.balance_paisa)} · {t("credit_limit")}: {money(value.credit_limit_paisa)}
          </div>
        </div>
        <button className="shrink-0 p-1 text-sm text-slate-400 hover:text-red-600" onClick={() => onChange(null)}>✕</button>
      </div>
    );
  }
  return (
    <div className="relative">
      <Input placeholder={`${t("walk_in")} — ${t("choose_customer")}`} value={q}
        onChange={(e) => setQ(e.target.value)} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 200)} />
      {open && data && data.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {data.map((c) => (
            <li key={c.id}>
              <button className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
                onMouseDown={() => { onChange(c); setQ(""); }}>
                <span className="truncate pr-2">{c.name} <span className="text-slate-500 text-xs">{c.phone}</span></span>
                <Badge value={c.type} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function NewSale() {
  const { t, money, qty, lang } = useI18n();
  const nav = useNavigate();
  const approval = useApproval();
  const [docType, setDocType] = useState<DocType>("invoice");
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [search, setSearch] = useState("");
  const [suggest, setSuggest] = useState<Product[]>([]);
  const [paid, setPaid] = useState("");
  const [payTouched, setPayTouched] = useState(false);
  const [tendered, setTendered] = useState("");
  const [method, setMethod] = useState("cash");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const paymentCardRef = useRef<HTMLDivElement>(null);
  const ds = useDebounced(search, 200);
  const { data: deliveryUsers } = useApi<User[]>(docType === "delivery" ? "/api/users?role=delivery" : null);

  const wholesale = customer?.type === "wholesale";
  const price = (p: Product) => (wholesale ? p.wholesale_price_paisa : p.retail_price_paisa);

  useEffect(() => {
    if (!ds.trim()) return setSuggest([]);
    let alive = true;
    api<Product[]>(`/api/products?limit=8&q=${encodeURIComponent(ds.trim())}`).then((r) => alive && setSuggest(r)).catch(() => {});
    return () => { alive = false; };
  }, [ds]);

  const lines = rows.map((r) => {
    const qty = toMilli(r.qty) ?? 0;
    const disc = toPaisa(r.discount) ?? 0;
    const gross = qty > 0 ? lineGross(price(r.product), qty) : 0;
    return { ...r, qtyMilli: qty, disc, gross, net: gross - disc };
  });
  const subtotal = lines.reduce((s, l) => s + l.gross, 0);
  const discount = lines.reduce((s, l) => s + l.disc, 0);
  const total = subtotal - discount;
  const paidPaisa = docType === "invoice" ? (payTouched ? toPaisa(paid) ?? 0 : total) : 0;
  const due = Math.max(total - paidPaisa, 0);
  const change = useMemo(() => {
    const tp = toPaisa(tendered);
    return tp !== null && tp > paidPaisa ? tp - paidPaisa : 0;
  }, [tendered, paidPaisa]);

  function addProduct(p: Product) {
    setRows((prev) => {
      const i = prev.findIndex((r) => r.product.id === p.id);
      if (i >= 0) {
        const copy = [...prev];
        const cur = toMilli(copy[i].qty) ?? 0;
        copy[i] = { ...copy[i], qty: fmtQty(cur + 1000) };
        return copy;
      }
      return [...prev, { product: p, qty: "1", discount: "" }];
    });
    setSearch("");
    setSuggest([]);
    searchRef.current?.focus();
  }

  async function onSearchEnter() {
    const code = search.trim();
    if (!code) return;
    try {
      addProduct(await api<Product>(`/api/products/lookup/${encodeURIComponent(code)}`)); // barcode / SKU
    } catch {
      if (suggest[0]) addProduct(suggest[0]);
    }
  }

  const invalid = lines.some((l) => l.qtyMilli <= 0 || l.disc < 0 || l.disc > l.gross) || rows.length === 0;

  async function submit() {
    setError(null);
    if (docType === "invoice" && paidPaisa > total) return setError(t("paid") + " > " + t("total"));
    setBusy(true);
    try {
      const doc = await approval.run((a) =>
        api<DocDetail>("/api/documents", {
          method: "POST",
          body: {
            doc_type: docType,
            customer_id: customer?.id ?? null,
            items: lines.map((l) => ({ product_id: l.product.id, qty: l.qty.trim(), discount_paisa: l.disc })),
            notes: notes || null,
            payment: docType === "invoice" && paidPaisa > 0 ? { amount_paisa: paidPaisa, method, reference: reference || null } : null,
            assigned_to_id: docType === "delivery" && assignedTo ? Number(assignedTo) : null,
            discount_approval: a.discount ?? null,
            credit_approval: a.credit ?? null,
          },
        }),
      );
      nav(`/documents/${doc.id}`);
    } catch (e) {
      if (!(e instanceof ApiError && e.code === "approval_cancelled")) setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {approval.modal}
      <PageHeader
        title={t("new_sale")}
        actions={
          <div className="flex w-full sm:w-auto rounded-lg border border-slate-300 bg-white p-0.5 shadow-2xs">
            {(["invoice", "estimate", "delivery"] as DocType[]).map((d) => (
              <button key={d} onClick={() => setDocType(d)}
                className={`flex-1 sm:flex-initial rounded-md px-3 py-1.5 text-xs sm:text-sm font-medium transition ${docType === d ? "bg-brand-600 text-white shadow-2xs" : "text-slate-700 hover:text-slate-900"}`}>
                {t(d)}
              </button>
            ))}
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("customer")}><CustomerPicker value={customer} onChange={setCustomer} /></Field>
              <div className="relative">
                <Field label={t("item")}>
                  <Input ref={searchRef} autoFocus placeholder={t("search_product")} value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); onSearchEnter(); } }} />
                </Field>
                {suggest.length > 0 && (
                  <ul className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl">
                    {suggest.map((p) => (
                      <li key={p.id}>
                        <button className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left text-sm hover:bg-slate-50 transition border-b border-slate-50 last:border-0" onClick={() => addProduct(p)}>
                          <span className="min-w-0">
                            <span className="block truncate font-medium">{lang === "bn" && p.name_bn ? p.name_bn : p.name}</span>
                            <span className="text-xs text-slate-500 font-mono">{p.sku}</span>
                          </span>
                          <span className="text-right text-xs shrink-0">
                            <div className="font-semibold text-slate-900">{money(price(p))}</div>
                            <div className={p.stock_milli <= 0 ? "font-medium text-red-600" : "text-slate-500"}>{t("in_stock")}: {qty(p.stock_milli)}</div>
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="mt-2 text-xs text-slate-500">{t("price_tier")}: <b className="text-slate-700">{t(wholesale ? "wholesale" : "retail")}</b></div>
          </Card>

          <Card title={`${t("items")} (${rows.length})`}>
            {rows.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">{t("no_items")}</p>
            ) : (
              <div className="space-y-2.5">
                {lines.map((l, i) => (
                  <div key={l.product.id} className="rounded-lg border border-slate-200/90 bg-white p-3 space-y-2 sm:space-y-0 sm:grid sm:grid-cols-12 sm:items-center sm:gap-2 shadow-2xs">
                    {/* Item header on mobile */}
                    <div className="flex items-start justify-between sm:col-span-4 sm:block">
                      <div className="min-w-0 pr-2">
                        <div className="font-medium text-sm text-slate-900 truncate">{lang === "bn" && l.product.name_bn ? l.product.name_bn : l.product.name}</div>
                        <div className="text-xs text-slate-500">{money(price(l.product))} / {t(l.product.unit)}</div>
                      </div>
                      <button className="p-1 text-slate-400 hover:text-red-600 sm:hidden" aria-label="Remove"
                        onClick={() => setRows(rows.filter((_, j) => j !== i))}>✕</button>
                    </div>

                    {/* Qty & Discount inputs */}
                    <div className="grid grid-cols-2 gap-2 sm:contents">
                      <div className="sm:col-span-2">
                        <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-400 sm:hidden">{t("qty")}</span>
                        <Input inputMode="decimal" aria-label={t("qty")} value={l.qty}
                          className={l.qtyMilli <= 0 ? "border-red-400" : ""}
                          onChange={(e) => setRows(rows.map((r, j) => (j === i ? { ...r, qty: e.target.value } : r)))} />
                      </div>
                      <div className="sm:col-span-2">
                        <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-400 sm:hidden">{t("discount")}</span>
                        <Input inputMode="decimal" placeholder="0" aria-label={t("discount")} value={l.discount}
                          className={l.disc > l.gross || toPaisa(l.discount) === null ? "border-red-400" : ""}
                          onChange={(e) => setRows(rows.map((r, j) => (j === i ? { ...r, discount: e.target.value } : r)))} />
                      </div>
                      <div className="col-span-2 flex items-center justify-between border-t border-slate-100 pt-2 sm:border-0 sm:pt-0 sm:col-span-3 sm:justify-end sm:text-right">
                        <span className="text-xs text-slate-500 sm:hidden">{t("total")}:</span>
                        <span className="text-sm font-bold tabular-nums text-slate-900">{money(l.net)}</span>
                      </div>
                      <button className="hidden sm:block sm:col-span-1 text-center text-slate-400 hover:text-red-600" aria-label="Remove"
                        onClick={() => setRows(rows.filter((_, j) => j !== i))}>✕</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Payment Summary Sidebar */}
        <div ref={paymentCardRef} className="space-y-4 lg:col-span-1">
          <Card title={t(docType)} className="h-fit lg:sticky lg:top-4">
            <dl className="space-y-1.5 text-sm">
              <div className="flex justify-between text-slate-600"><dt>{t("subtotal")}</dt><dd className="tabular-nums font-medium">{money(subtotal)}</dd></div>
              <div className="flex justify-between text-slate-600"><dt>{t("discount")}</dt><dd className="tabular-nums font-medium text-emerald-700">- {money(discount)}</dd></div>
              <div className="flex justify-between border-t border-slate-200 pt-2.5 text-base sm:text-lg font-bold text-slate-900"><dt>{t("total")}</dt><dd className="tabular-nums">{money(total)}</dd></div>
            </dl>

            {docType === "invoice" && (
              <div className="mt-4 space-y-3 border-t border-slate-100 pt-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-2.5">
                  <Field label={t("paid")}>
                    <div className="flex gap-1.5">
                      <Input inputMode="decimal" value={payTouched ? paid : paisaToInput(total)}
                        onChange={(e) => { setPayTouched(true); setPaid(e.target.value); }} />
                      <Button variant="secondary" type="button" className="shrink-0 text-xs px-2.5" onClick={() => { setPayTouched(false); setPaid(""); }}>{t("pay_full")}</Button>
                    </div>
                  </Field>
                  <Field label={t("method")}>
                    <Select value={method} onChange={(e) => setMethod(e.target.value)}>
                      {["cash", "bkash", "nagad", "bank"].map((m) => <option key={m} value={m}>{t(m as "cash")}</option>)}
                    </Select>
                  </Field>
                </div>
                {method === "cash" ? (
                  <Field label={t("tendered")} hint={change > 0 ? `${t("change")}: ${money(change)}` : undefined}>
                    <Input inputMode="decimal" value={tendered} onChange={(e) => setTendered(e.target.value)} />
                  </Field>
                ) : (
                  <Field label={t("reference")}><Input value={reference} onChange={(e) => setReference(e.target.value)} /></Field>
                )}
                <div className={`flex justify-between rounded-lg px-3 py-2 text-sm font-semibold ${due > 0 ? "bg-red-50 text-red-700 border border-red-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200"}`}>
                  <span>{t("due")}</span><span className="tabular-nums">{money(due)}</span>
                </div>
              </div>
            )}

            {docType === "delivery" && (
              <div className="mt-4 border-t border-slate-100 pt-3">
                <Field label={t("assigned_to")}>
                  <Select value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)}>
                    <option value="">{t("none")}</option>
                    {deliveryUsers?.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                  </Select>
                </Field>
              </div>
            )}

            <div className="mt-3">
              <Field label={`${t("notes")} (${t("optional")})`}><Input value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            </div>
            <div className="mt-4 space-y-2">
              <ErrorText>{error}</ErrorText>
              <Button className="w-full py-3 text-base font-semibold shadow-md" disabled={busy || invalid} onClick={submit}>
                {t("save")} {t(docType)}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
