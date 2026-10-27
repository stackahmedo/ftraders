import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, ErrorText, Field, Input, Modal, PageHeader, Select, Table, td, tdNum } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi, useDebounced } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import { paisaToInput, toPaisa } from "../lib/money";
import type { Customer, CustomerType } from "../lib/types";

const EMPTY = { name: "", phone: "", address: "", type: "retail" as CustomerType, limit: "0", opening: "0", notes: "", is_active: true };
type Form = typeof EMPTY;

export function CustomerForm({ initial, onSaved, onClose }: { initial: Customer | null; onSaved: () => void; onClose: () => void }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const [form, setForm] = useState<Form>(initial ? {
    name: initial.name, phone: initial.phone ?? "", address: initial.address ?? "", type: initial.type,
    limit: paisaToInput(initial.credit_limit_paisa), opening: paisaToInput(initial.opening_balance_paisa),
    notes: initial.notes ?? "", is_active: initial.is_active,
  } : EMPTY);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof Form, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));
  const creditOk = can("customers.credit");

  async function save() {
    const limit = toPaisa(form.limit);
    const opening = toPaisa(form.opening);
    if (limit === null || opening === null) return setErr("Check amounts");
    setBusy(true);
    setErr(null);
    try {
      const body = { name: form.name, phone: form.phone || null, address: form.address || null, type: form.type,
        credit_limit_paisa: limit, opening_balance_paisa: opening, notes: form.notes || null, is_active: form.is_active };
      if (initial) await api(`/api/customers/${initial.id}`, { method: "PUT", body });
      else await api("/api/customers", { method: "POST", body });
      onSaved();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title={initial ? t("edit") : t("add")} onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>{t("cancel")}</Button><Button disabled={busy || !form.name} onClick={save}>{t("save")}</Button></>}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label={t("name")}><Input autoFocus value={form.name} onChange={(e) => set("name", e.target.value)} /></Field>
        <Field label={t("phone")}><Input inputMode="tel" value={form.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
      </div>
      <Field label={t("address")}><Input value={form.address} onChange={(e) => set("address", e.target.value)} /></Field>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Field label={t("type")}>
          <Select disabled={!creditOk} value={form.type} onChange={(e) => set("type", e.target.value)}>
            {(["retail", "wholesale", "credit"] as const).map((x) => <option key={x} value={x}>{t(x)}</option>)}
          </Select>
        </Field>
        <Field label={`${t("credit_limit")} (৳)`}><Input disabled={!creditOk} inputMode="decimal" value={form.limit} onChange={(e) => set("limit", e.target.value)} /></Field>
        <Field label={`${t("opening_balance")} (৳)`}><Input disabled={!creditOk} inputMode="decimal" value={form.opening} onChange={(e) => set("opening", e.target.value)} /></Field>
      </div>
      <Field label={t("notes")}><Input value={form.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} className="rounded" /> {t("active")}
      </label>
      <ErrorText>{err}</ErrorText>
    </Modal>
  );
}

export default function Customers() {
  const { t, money } = useI18n();
  const { can } = useAuth();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const dq = useDebounced(q);
  const { data, error, reload } = useApi<Customer[]>(`/api/customers?active_only=false&q=${encodeURIComponent(dq)}${type ? `&type=${type}` : ""}`);
  const [editing, setEditing] = useState<Customer | "new" | null>(null);

  return (
    <div className="space-y-4">
      <PageHeader title={t("customers")} actions={can("customers.write") && <Button onClick={() => setEditing("new")}>＋ {t("add")}</Button>} />
      <Card>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <Input className="sm:col-span-2" placeholder={`${t("search")}: ${t("name")}, ${t("phone")}`} value={q} onChange={(e) => setQ(e.target.value)} />
          <Select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">{t("type")}: {t("all")}</option>
            {(["retail", "wholesale", "credit"] as const).map((x) => <option key={x} value={x}>{t(x)}</option>)}
          </Select>
        </div>
      </Card>
      <ErrorText>{error}</ErrorText>
      <Card>
        <Table head={[t("name"), t("phone"), t("type"), t("credit_limit"), t("balance"), ""]} empty={data?.length === 0}>
          {data?.map((c) => (
            <tr key={c.id} className={c.is_active ? "" : "opacity-50"}>
              <td className={td}>
                <Link className="font-semibold text-brand-700 hover:underline" to={`/customers/${c.id}`}>{c.name}</Link>
                {c.address && <div className="text-xs text-slate-500 max-w-xs truncate">{c.address}</div>}
              </td>
              <td className={td}>{c.phone ? <a className="text-slate-700 hover:text-brand-700" href={`tel:${c.phone}`}>{c.phone}</a> : "—"}</td>
              <td className={td}><Badge value={c.type} /></td>
              <td className={tdNum}>{money(c.credit_limit_paisa)}</td>
              <td className={`${tdNum} font-bold ${c.balance_paisa > 0 ? "text-red-600" : "text-emerald-700"}`}>{money(c.balance_paisa)}</td>
              <td className={td}>{can("customers.write") && <button className="text-sm font-medium text-brand-700 hover:underline" onClick={() => setEditing(c)}>{t("edit")}</button>}</td>
            </tr>
          ))}
        </Table>
      </Card>
      {editing && (
        <CustomerForm
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload(); }}
        />
      )}
    </div>
  );
}
