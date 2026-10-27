import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, ErrorText, Field, Input, Modal, PageHeader, Select, Table, td, tdNum, useApproval } from "../components/ui";
import { api, ApiError, openPdf } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import { paisaToInput, toPaisa } from "../lib/money";
import type { DocDetail, DocType, Payment, User } from "../lib/types";

type Dialog =
  | { kind: "pay" }
  | { kind: "void" }
  | { kind: "plan" }
  | { kind: "convert"; target: DocType }
  | { kind: "reverse"; payment: Payment }
  | null;

export default function DocumentDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { t, money, qty, dt, tv } = useI18n();
  const { can } = useAuth();
  const approval = useApproval();
  const { data: doc, error, reload } = useApi<DocDetail>(`/api/documents/${id}`);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [dlgError, setDlgError] = useState<string | null>(null);
  const { data: deliveryUsers } = useApi<User[]>(dialog?.kind === "convert" && dialog.target === "delivery" ? "/api/users?role=delivery" : null);

  if (error) return <ErrorText>{error}</ErrorText>;
  if (!doc) return <div className="py-8 text-center text-slate-500">{t("loading")}</div>;

  const isVoid = doc.status === "void";
  const verifyUrl = `${window.location.origin}/verify/${doc.verify_token}`;
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  function openDialog(d: Dialog, defaults: Record<string, string> = {}) {
    setForm(defaults);
    setDlgError(null);
    setDialog(d);
  }

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setDlgError(null);
    try {
      await fn();
      setDialog(null);
      reload();
    } catch (e) {
      if (!(e instanceof ApiError && e.code === "approval_cancelled")) setDlgError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function print(layout: "a4" | "thermal") {
    try {
      await openPdf(doc!.id, layout);
    } catch (e) {
      alert((e as Error).message);
    }
  }

  const canConvert = can("docs.write") && doc.status === "open";
  const targets: DocType[] = doc.doc_type === "estimate" ? ["delivery", "invoice"] : doc.doc_type === "delivery" ? ["invoice"] : [];

  return (
    <div className="space-y-4">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            <span>{t(doc.doc_type)} <b className="text-brand-900">{doc.number}</b></span>
            <Badge value={doc.status} />
            {!isVoid && <Badge value={doc.payment_status} />}
          </span>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <Button variant="secondary" className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => print("a4")}>🖨 {t("print_a4")}</Button>
            <Button variant="secondary" className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => print("thermal")}>🧾 {t("print_thermal")}</Button>
            {canConvert && targets.map((tg) => (
              <Button key={tg} className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => openDialog({ kind: "convert", target: tg }, tg === "invoice" ? { amount: "", method: "cash" } : {})}>
                {t("convert_to")} {t(tg)}
              </Button>
            ))}
            {doc.doc_type === "invoice" && !isVoid && doc.due_paisa > 0 && can("payments.write") && (
              <>
                <Button className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => openDialog({ kind: "pay" }, { amount: paisaToInput(doc.due_paisa), method: "cash" })}>{t("add_payment")}</Button>
                <Button variant="secondary" className="flex-1 sm:flex-initial text-xs sm:text-sm" onClick={() => openDialog({ kind: "plan" }, { count: "3", first_due: new Date().toISOString().slice(0, 10), interval: "30" })}>{t("make_plan")}</Button>
              </>
            )}
            {!isVoid && can("docs.void") && <Button variant="danger" className="w-full sm:w-auto text-xs sm:text-sm" onClick={() => openDialog({ kind: "void" })}>{t("void_document")}</Button>}
          </div>
        }
      />

      {isVoid && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <b>{t("void")}</b> — {doc.void_reason} · {t("voided_by")}: {doc.voided_by_name} · {doc.voided_at && dt(doc.voided_at)}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-3 sm:gap-4 grid-cols-1 md:grid-cols-3">
        <Card title={t("customer")}>
          <div className="space-y-1 text-sm">
            <div className="font-semibold text-slate-900">
              {doc.customer_id ? <Link className="text-brand-700 hover:underline" to={`/customers/${doc.customer_id}`}>{doc.customer_name}</Link> : doc.customer_name}
            </div>
            {doc.customer_phone && <div className="text-slate-600">{doc.customer_phone}</div>}
            {doc.customer_address && <div className="text-slate-500 text-xs">{doc.customer_address}</div>}
            <div className="pt-2 text-xs text-slate-500">{t("price_tier")}: <b className="text-slate-700">{tv(doc.price_tier)}</b></div>
          </div>
        </Card>
        <Card title={t("date")}>
          <dl className="space-y-1.5 text-sm">
            <div className="flex justify-between text-slate-600"><dt>{t("created")}</dt><dd className="font-medium text-slate-900">{dt(doc.created_at)}</dd></div>
            <div className="flex justify-between text-slate-600"><dt>{t("prepared_by")}</dt><dd className="font-medium text-slate-900">{doc.created_by_name}</dd></div>
            {doc.approved_by_name && <div className="flex justify-between text-slate-600"><dt>{t("approved_by")}</dt><dd className="font-medium text-slate-900">{doc.approved_by_name}</dd></div>}
            {doc.assigned_to_name && <div className="flex justify-between text-slate-600"><dt>{t("assigned_to")}</dt><dd className="font-medium text-slate-900">{doc.assigned_to_name}</dd></div>}
            {doc.parent_id && <div className="flex justify-between text-slate-600"><dt>{t("source")}</dt><dd><Link className="text-brand-700 hover:underline font-medium" to={`/documents/${doc.parent_id}`}>{doc.parent_number}</Link></dd></div>}
            {doc.children.length > 0 && (
              <div className="flex justify-between text-slate-600"><dt>{t("made_from_this")}</dt>
                <dd className="space-x-2">{doc.children.map((c) => <Link key={c.id} className="text-brand-700 hover:underline font-medium" to={`/documents/${c.id}`}>{c.number}{c.status === "void" ? " (void)" : ""}</Link>)}</dd>
              </div>
            )}
          </dl>
        </Card>
        <Card title={t("total")}>
          <dl className="space-y-1.5 text-sm">
            <div className="flex justify-between text-slate-600"><dt>{t("subtotal")}</dt><dd className="tabular-nums font-medium">{money(doc.subtotal_paisa)}</dd></div>
            <div className="flex justify-between text-slate-600"><dt>{t("discount")}</dt><dd className="tabular-nums font-medium text-emerald-700">- {money(doc.discount_paisa)}</dd></div>
            <div className="flex justify-between border-t border-slate-200 pt-1.5 font-bold text-slate-900"><dt>{t("total")}</dt><dd className="tabular-nums">{money(doc.total_paisa)}</dd></div>
            {doc.doc_type === "invoice" && (
              <>
                <div className="flex justify-between text-slate-600"><dt>{t("paid")}</dt><dd className="tabular-nums font-medium text-emerald-700">{money(doc.paid_paisa)}</dd></div>
                <div className={`flex justify-between font-bold ${doc.due_paisa > 0 ? "text-red-600" : "text-emerald-700"}`}><dt>{t("due")}</dt><dd className="tabular-nums">{money(doc.due_paisa)}</dd></div>
              </>
            )}
          </dl>
          <a className="mt-3 block truncate text-xs text-brand-700 hover:underline" href={verifyUrl} target="_blank" rel="noreferrer">🔗 {verifyUrl}</a>
        </Card>
      </div>

      {/* Items Card */}
      <Card title={t("items")}>
        <Table head={["#", t("item"), t("qty"), t("rate"), t("discount"), t("amount")]}>
          {doc.items.map((i) => (
            <tr key={i.id}>
              <td className={td}><span className="text-xs text-slate-400">{i.line_no}</span></td>
              <td className={td}><span className="font-medium text-slate-900">{i.description}</span></td>
              <td className={tdNum}>{qty(i.qty_milli)} {tv(i.unit)}</td>
              <td className={tdNum}>{money(i.unit_price_paisa)}</td>
              <td className={tdNum}>{i.discount_paisa ? money(i.discount_paisa) : "—"}</td>
              <td className={`${tdNum} font-semibold text-slate-900`}>{money(i.line_total_paisa)}</td>
            </tr>
          ))}
        </Table>
        {doc.notes && <p className="mt-3 text-sm text-slate-600 border-t border-slate-100 pt-2"><b>{t("notes")}:</b> {doc.notes}</p>}
      </Card>

      {/* Payments and Installments */}
      {doc.doc_type === "invoice" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title={t("paid")}>
            <Table head={[t("date"), t("method"), t("amount"), t("prepared_by"), ""]} empty={doc.payments.length === 0}>
              {doc.payments.map((p) => (
                <tr key={p.id} className={p.amount_paisa < 0 || p.is_reversed ? "text-slate-400" : ""}>
                  <td className={td}><span className="text-xs sm:text-sm">{dt(p.paid_at)}</span></td>
                  <td className={td}><span className="font-medium">{tv(p.method)}</span> {p.reference && <span className="text-xs text-slate-500">({p.reference})</span>}</td>
                  <td className={`${tdNum} ${p.amount_paisa < 0 ? "text-red-600" : "font-semibold text-emerald-700"}`}>{money(p.amount_paisa)}</td>
                  <td className={td}><span className="text-xs sm:text-sm">{p.user_name}</span>{p.note && <div className="text-xs text-slate-500">{p.note}</div>}</td>
                  <td className={td}>
                    {p.amount_paisa > 0 && !p.is_reversed && !isVoid && can("payments.reverse") && (
                      <button className="text-xs font-medium text-red-600 hover:underline" onClick={() => openDialog({ kind: "reverse", payment: p })}>{t("reverse")}</button>
                    )}
                  </td>
                </tr>
              ))}
            </Table>
          </Card>
          {doc.installments.length > 0 && (
            <Card title={t("installments")}>
              <Table head={["#", t("due_date"), t("amount"), t("paid"), t("status")]}>
                {doc.installments.map((i) => (
                  <tr key={i.id}>
                    <td className={td}><span className="text-xs text-slate-400">{i.seq}</span></td>
                    <td className={`${td} ${i.is_overdue ? "font-semibold text-red-600" : ""}`}>{i.due_date}{i.is_overdue && ` · ${t("overdue")}`}</td>
                    <td className={tdNum}>{money(i.amount_paisa)}</td>
                    <td className={tdNum}>{money(i.paid_paisa)}</td>
                    <td className={td}><Badge value={i.is_paid ? "paid" : i.paid_paisa > 0 ? "partial" : "due"} /></td>
                  </tr>
                ))}
              </Table>
            </Card>
          )}
        </div>
      )}

      {/* ------------------------------------------------ dialogs */}
      <Modal open={dialog?.kind === "pay"} title={t("add_payment")} onClose={() => setDialog(null)}
        footer={<Button disabled={busy || !toPaisa(form.amount ?? "")} onClick={() => act(() => api("/api/payments", { method: "POST", body: {
          document_id: doc.id, amount_paisa: toPaisa(form.amount ?? ""), method: form.method, reference: form.reference || null } }))}>{t("save")}</Button>}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label={`${t("amount")} (${t("due")}: ${money(doc.due_paisa)})`}><Input inputMode="decimal" value={form.amount ?? ""} onChange={(e) => set("amount", e.target.value)} /></Field>
          <Field label={t("method")}>
            <Select value={form.method} onChange={(e) => set("method", e.target.value)}>
              {["cash", "bkash", "nagad", "bank"].map((m) => <option key={m} value={m}>{tv(m)}</option>)}
            </Select>
          </Field>
        </div>
        <Field label={t("reference")}><Input value={form.reference ?? ""} onChange={(e) => set("reference", e.target.value)} /></Field>
        <ErrorText>{dlgError}</ErrorText>
      </Modal>

      <Modal open={dialog?.kind === "plan"} title={t("make_plan")} onClose={() => setDialog(null)}
        footer={<Button disabled={busy} onClick={() => act(() => api(`/api/documents/${doc.id}/installments`, { method: "POST", body: {
          count: Number(form.count), first_due: form.first_due, interval_days: Number(form.interval) } }))}>{t("save")}</Button>}>
        <p className="text-sm text-slate-600">{t("due")}: <b className="text-red-600">{money(doc.due_paisa)}</b></p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field label={t("count")}><Input type="number" min={1} max={60} value={form.count ?? ""} onChange={(e) => set("count", e.target.value)} /></Field>
          <Field label={t("first_due")}><Input type="date" value={form.first_due ?? ""} onChange={(e) => set("first_due", e.target.value)} /></Field>
          <Field label={t("every_days")}><Input type="number" min={1} value={form.interval ?? ""} onChange={(e) => set("interval", e.target.value)} /></Field>
        </div>
        <ErrorText>{dlgError}</ErrorText>
      </Modal>

      <Modal open={dialog?.kind === "void"} title={`${t("void_document")} ${doc.number}`} onClose={() => setDialog(null)}
        footer={<Button variant="danger" disabled={busy || (form.reason ?? "").trim().length < 3}
          onClick={() => act(() => api(`/api/documents/${doc.id}/void`, { method: "POST", body: { reason: form.reason } }))}>{t("void_document")}</Button>}>
        <Field label={t("reason")}><Input autoFocus value={form.reason ?? ""} onChange={(e) => set("reason", e.target.value)} /></Field>
        <ErrorText>{dlgError}</ErrorText>
      </Modal>

      <Modal open={dialog?.kind === "reverse"} title={t("reverse")} onClose={() => setDialog(null)}
        footer={<Button variant="danger" disabled={busy || (form.reason ?? "").trim().length < 3}
          onClick={() => dialog?.kind === "reverse" && act(() => api(`/api/payments/${dialog.payment.id}/reverse`, { method: "POST", body: { reason: form.reason } }))}>{t("reverse")}</Button>}>
        {dialog?.kind === "reverse" && <p className="text-sm bg-slate-50 p-2.5 rounded-lg border border-slate-200">{money(dialog.payment.amount_paisa)} · {tv(dialog.payment.method)} · {dt(dialog.payment.paid_at)}</p>}
        <Field label={t("reason")}><Input autoFocus value={form.reason ?? ""} onChange={(e) => set("reason", e.target.value)} /></Field>
        <ErrorText>{dlgError}</ErrorText>
      </Modal>

      <Modal open={dialog?.kind === "convert"} title={dialog?.kind === "convert" ? `${t("convert_to")} ${t(dialog.target)}` : ""} onClose={() => setDialog(null)}
        footer={<Button disabled={busy} onClick={() => dialog?.kind === "convert" && act(async () => {
          const target = dialog.target;
          const amount = target === "invoice" ? toPaisa(form.amount ?? "") ?? 0 : 0;
          const child = await approval.run((a) => api<DocDetail>(`/api/documents/${doc.id}/convert`, { method: "POST", body: {
            target_type: target,
            payment: amount > 0 ? { amount_paisa: amount, method: form.method ?? "cash", reference: form.reference || null } : null,
            assigned_to_id: form.assigned ? Number(form.assigned) : null,
            credit_approval: a.credit ?? null } }));
          nav(`/documents/${child.id}`);
        })}>{t("create")}</Button>}>
        <p className="text-sm text-slate-600">{t("total")}: <b className="text-slate-900">{money(doc.total_paisa)}</b></p>
        {dialog?.kind === "convert" && dialog.target === "invoice" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field label={t("paid")}><Input inputMode="decimal" value={form.amount ?? ""} placeholder="0" onChange={(e) => set("amount", e.target.value)} /></Field>
            <Field label={t("method")}>
              <Select value={form.method ?? "cash"} onChange={(e) => set("method", e.target.value)}>
                {["cash", "bkash", "nagad", "bank"].map((m) => <option key={m} value={m}>{tv(m)}</option>)}
              </Select>
            </Field>
          </div>
        )}
        {dialog?.kind === "convert" && dialog.target === "delivery" && (
          <Field label={t("assigned_to")}>
            <Select value={form.assigned ?? ""} onChange={(e) => set("assigned", e.target.value)}>
              <option value="">{t("none")}</option>
              {deliveryUsers?.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
            </Select>
          </Field>
        )}
        <ErrorText>{dlgError}</ErrorText>
      </Modal>
      {approval.modal /* last, so it stacks above the convert dialog */}
    </div>
  );
}
