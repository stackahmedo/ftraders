import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, Button, Card, ErrorText, Field, Input, Modal, PageHeader, Select, Table, td, tdNum } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import { toPaisa } from "../lib/money";
import type { Customer, DocSummary } from "../lib/types";
import { CustomerForm } from "./Customers";

interface Ledger {
  customer: Customer;
  opening_balance_paisa: number;
  balance_paisa: number;
  entries: { at: string; kind: string; ref: string | null; document_id: number | null; debit_paisa: number; credit_paisa: number; balance_paisa: number; note: string | null }[];
}

const KIND_LABEL: Record<string, string> = { invoice: "invoice", invoice_void: "void", payment: "paid", payment_reversal: "reverse" };

export default function CustomerLedger() {
  const { id } = useParams();
  const { t, money, dt, tv } = useI18n();
  const { can } = useAuth();
  const { data, error, reload } = useApi<Ledger>(`/api/customers/${id}/ledger`);
  const { data: dueDocs, reload: reloadDocs } = useApi<DocSummary[]>(`/api/documents?type=invoice&customer_id=${id}`);
  const [editing, setEditing] = useState(false);
  const [paying, setPaying] = useState(false);
  const [form, setForm] = useState({ amount: "", method: "cash", reference: "", document: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!data) return <div className="py-8 text-center text-slate-500">{t("loading")}</div>;
  const c = data.customer;
  const open = (dueDocs ?? []).filter((d) => d.status !== "void" && d.due_paisa > 0).reverse(); // oldest first

  async function receive() {
    const amount = toPaisa(form.amount);
    if (!amount) return setErr("Enter an amount");
    setBusy(true);
    setErr(null);
    try {
      await api("/api/payments", { method: "POST", body: {
        amount_paisa: amount, method: form.method, reference: form.reference || null,
        document_id: form.document ? Number(form.document) : null, customer_id: form.document ? null : c.id } });
      setPaying(false);
      reload();
      reloadDocs();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title={<span className="flex flex-wrap items-center gap-2"><span>{c.name}</span> <Badge value={c.type} /></span>}
        actions={
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {can("payments.write") && <Button className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => { setErr(null); setForm({ amount: "", method: "cash", reference: "", document: open[0] ? String(open[0].id) : "" }); setPaying(true); }}>💰 {t("receive_payment")}</Button>}
            {can("customers.write") && <Button variant="secondary" className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => setEditing(true)}>{t("edit")}</Button>}
          </div>
        }
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card><div className="text-xs text-slate-500">{t("phone")}</div><div className="font-semibold text-slate-900 truncate">{c.phone ?? "—"}</div><div className="text-xs text-slate-500 truncate">{c.address}</div></Card>
        <Card><div className="text-xs text-slate-500">{t("credit_limit")}</div><div className="text-base sm:text-lg font-bold text-slate-900">{money(c.credit_limit_paisa)}</div></Card>
        <Card><div className="text-xs text-slate-500">{t("opening_balance")}</div><div className="text-base sm:text-lg font-bold text-slate-900">{money(data.opening_balance_paisa)}</div></Card>
        <Card><div className="text-xs text-slate-500">{t("balance")}</div><div className={`text-base sm:text-lg font-bold ${data.balance_paisa > 0 ? "text-red-600" : "text-emerald-700"}`}>{money(data.balance_paisa)}</div></Card>
      </div>

      <Card title={t("ledger")}>
        <Table head={[t("date"), t("type"), t("number"), t("debit"), t("credit_col"), t("balance")]} empty={data.entries.length === 0}>
          {data.entries.map((e, i) => (
            <tr key={i}>
              <td className={td}><span className="text-xs sm:text-sm">{dt(e.at)}</span></td>
              <td className={td}><span className="font-medium text-slate-900">{tv(KIND_LABEL[e.kind] ?? e.kind)}</span>{e.note && <div className="text-xs text-slate-500">{e.note}</div>}</td>
              <td className={td}>{e.document_id ? <Link className="font-medium text-brand-700 hover:underline" to={`/documents/${e.document_id}`}>{e.ref}</Link> : "—"}</td>
              <td className={`${tdNum} text-slate-900`}>{e.debit_paisa ? money(e.debit_paisa) : ""}</td>
              <td className={`${tdNum} text-emerald-700 font-medium`}>{e.credit_paisa ? money(e.credit_paisa) : ""}</td>
              <td className={`${tdNum} font-bold text-slate-900`}>{money(e.balance_paisa)}</td>
            </tr>
          ))}
        </Table>
      </Card>

      {editing && <CustomerForm initial={c} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); reload(); }} />}
      <Modal open={paying} title={t("receive_payment")} onClose={() => setPaying(false)}
        footer={<Button disabled={busy} onClick={receive}>{t("save")}</Button>}>
        <Field label={t("invoice")}>
          <Select value={form.document} onChange={(e) => setForm({ ...form, document: e.target.value })}>
            {open.map((d) => <option key={d.id} value={d.id}>{d.number} — {t("due")} {money(d.due_paisa)}</option>)}
            <option value="">{t("none")} ({t("balance")})</option>
          </Select>
        </Field>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label={t("amount")}><Input inputMode="decimal" autoFocus value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
          <Field label={t("method")}>
            <Select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
              {["cash", "bkash", "nagad", "bank"].map((m) => <option key={m} value={m}>{tv(m)}</option>)}
            </Select>
          </Field>
        </div>
        <Field label={`${t("reference")} (${t("optional")})`}>
          <Input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
        </Field>
        <ErrorText>{err}</ErrorText>
      </Modal>
    </div>
  );
}
