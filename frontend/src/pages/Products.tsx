import { useState } from "react";
import { Button, Card, ErrorText, Field, Input, Modal, PageHeader, Select, Table, td, tdNum } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi, useDebounced } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import { fmtQty, paisaToInput, toMilli, toPaisa } from "../lib/money";
import type { Product } from "../lib/types";

const EMPTY = { name: "", name_bn: "", sku: "", barcode: "", category: "", unit: "piece", buy: "", retail: "", wholesale: "", low: "0", is_active: true };
type Form = typeof EMPTY;

export default function Products() {
  const { t, money, qty, lang } = useI18n();
  const { can } = useAuth();
  const [q, setQ] = useState("");
  const dq = useDebounced(q);
  const { data, error, reload } = useApi<Product[]>(`/api/products?active_only=false&q=${encodeURIComponent(dq)}`);
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [form, setForm] = useState<Form>(EMPTY);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof Form, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  function open(p: Product | "new") {
    setErr(null);
    setEditing(p);
    setForm(p === "new" ? EMPTY : {
      name: p.name, name_bn: p.name_bn ?? "", sku: p.sku, barcode: p.barcode ?? "", category: p.category_name ?? "",
      unit: p.unit, buy: paisaToInput(p.buy_price_paisa), retail: paisaToInput(p.retail_price_paisa),
      wholesale: paisaToInput(p.wholesale_price_paisa), low: fmtQty(p.low_stock_milli), is_active: p.is_active,
    });
  }

  async function save() {
    const buy = toPaisa(form.buy), retail = toPaisa(form.retail), wholesale = toPaisa(form.wholesale);
    if (buy === null || retail === null || wholesale === null || toMilli(form.low) === null) {
      return setErr("Check prices and low-stock level");
    }
    setBusy(true);
    setErr(null);
    try {
      const body = {
        name: form.name, name_bn: form.name_bn || null, sku: form.sku, barcode: form.barcode || null,
        category: form.category || null, unit: form.unit, buy_price_paisa: buy, retail_price_paisa: retail,
        wholesale_price_paisa: wholesale, low_stock: form.low, is_active: form.is_active,
      };
      if (editing === "new") await api("/api/products", { method: "POST", body });
      else if (editing) await api(`/api/products/${editing.id}`, { method: "PUT", body });
      setEditing(null);
      reload();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title={t("products")} actions={can("products.write") && <Button onClick={() => open("new")}>＋ {t("add")}</Button>} />
      <Card>
        <Input placeholder={`${t("search")}: ${t("name")}, ${t("sku")}, ${t("barcode")}`} value={q} onChange={(e) => setQ(e.target.value)} />
      </Card>
      <ErrorText>{error}</ErrorText>
      <Card>
        <Table head={[t("name"), t("sku"), t("category"), t("buy_price"), t("retail_price"), t("wholesale_price"), t("in_stock"), ""]}
          empty={data?.length === 0}>
          {data?.map((p) => (
            <tr key={p.id} className={p.is_active ? "" : "opacity-50"}>
              <td className={td}>
                <div className="font-semibold text-slate-900">{lang === "bn" && p.name_bn ? p.name_bn : p.name}</div>
                {p.barcode && <div className="text-xs text-slate-400 font-mono">{p.barcode}</div>}
              </td>
              <td className={td}><span className="font-mono text-xs sm:text-sm text-slate-600">{p.sku}</span></td>
              <td className={td}><span className="text-xs sm:text-sm text-slate-600">{p.category_name ?? "—"}</span></td>
              <td className={tdNum}>{money(p.buy_price_paisa)}</td>
              <td className={`${tdNum} font-medium`}>{money(p.retail_price_paisa)}</td>
              <td className={tdNum}>{money(p.wholesale_price_paisa)}</td>
              <td className={`${tdNum} ${p.stock_milli <= p.low_stock_milli ? "font-bold text-red-600" : "font-medium text-slate-900"}`}>{qty(p.stock_milli)} {t(p.unit)}</td>
              <td className={td}>{can("products.write") && <button className="text-sm font-medium text-brand-700 hover:underline" onClick={() => open(p)}>{t("edit")}</button>}</td>
            </tr>
          ))}
        </Table>
      </Card>

      <Modal open={editing !== null} title={editing === "new" ? t("add") : t("edit")} onClose={() => setEditing(null)}
        footer={<><Button variant="secondary" onClick={() => setEditing(null)}>{t("cancel")}</Button>
          <Button disabled={busy || !form.name || !form.sku} onClick={save}>{t("save")}</Button></>}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label={t("name")}><Input autoFocus value={form.name} onChange={(e) => set("name", e.target.value)} /></Field>
          <Field label={t("name_bn")}><Input value={form.name_bn} onChange={(e) => set("name_bn", e.target.value)} /></Field>
          <Field label={t("sku")}><Input value={form.sku} onChange={(e) => set("sku", e.target.value)} /></Field>
          <Field label={t("barcode")}><Input value={form.barcode} onChange={(e) => set("barcode", e.target.value)} /></Field>
          <Field label={t("category")}><Input value={form.category} onChange={(e) => set("category", e.target.value)} /></Field>
          <Field label={t("unit")}>
            <Select value={form.unit} onChange={(e) => set("unit", e.target.value)}>
              {(["piece", "carton", "kg"] as const).map((u) => <option key={u} value={u}>{t(u)}</option>)}
            </Select>
          </Field>
          <Field label={`${t("buy_price")} (৳)`}><Input inputMode="decimal" value={form.buy} onChange={(e) => set("buy", e.target.value)} /></Field>
          <Field label={`${t("retail_price")} (৳)`}><Input inputMode="decimal" value={form.retail} onChange={(e) => set("retail", e.target.value)} /></Field>
          <Field label={`${t("wholesale_price")} (৳)`}><Input inputMode="decimal" value={form.wholesale} onChange={(e) => set("wholesale", e.target.value)} /></Field>
          <Field label={t("low_stock_level")}><Input inputMode="decimal" value={form.low} onChange={(e) => set("low", e.target.value)} /></Field>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700 pt-1">
          <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} className="rounded" /> {t("active")}
        </label>
        <ErrorText>{err}</ErrorText>
      </Modal>
    </div>
  );
}
