import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, ErrorText, Field, Input, PageHeader, Select, Table, td, tdNum } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import { toMilli } from "../lib/money";
import type { LowStock, Movement, Product } from "../lib/types";

const TYPES = ["stock_in", "return", "adjustment", "damage"] as const;

export default function Stock() {
  const { t, qty, dt, tv, lang } = useI18n();
  const { can } = useAuth();
  const [productFilter, setProductFilter] = useState("");
  const { data: products } = useApi<Product[]>("/api/products?limit=2000");
  const { data: moves, reload } = useApi<Movement[]>(`/api/stock/movements${productFilter ? `?product_id=${productFilter}` : ""}`);
  const { data: low, reload: reloadLow } = useApi<LowStock[]>("/api/stock/low");
  const [form, setForm] = useState({ product: "", type: "stock_in", qty: "", reason: "", reference: "" });
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const name = (p: { name: string; name_bn: string | null }) => (lang === "bn" && p.name_bn ? p.name_bn : p.name);

  const needsReason = form.type === "adjustment" || form.type === "damage";
  const q = toMilli(form.qty);

  async function submit() {
    setBusy(true);
    setErr(null);
    setOk(null);
    try {
      await api("/api/stock/movements", { method: "POST", body: {
        product_id: Number(form.product), type: form.type, qty: form.qty.trim(),
        reason: form.reason || null, reference: form.reference || null } });
      setOk(t("saved"));
      setForm({ ...form, qty: "", reason: "", reference: "" });
      reload();
      reloadLow();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title={t("stock")} />
      <div className="grid gap-4 lg:grid-cols-3">
        {can("stock.write") && (
          <Card title={t("record_movement")}>
            <div className="space-y-3">
              <Field label={t("item")}>
                <Select value={form.product} onChange={(e) => setForm({ ...form, product: e.target.value })}>
                  <option value="">—</option>
                  {products?.map((p) => <option key={p.id} value={p.id}>{name(p)} ({qty(p.stock_milli)} {tv(p.unit)})</option>)}
                </Select>
              </Field>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <Field label={t("type")}>
                  <Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                    {TYPES.map((x) => <option key={x} value={x}>{t(x)}</option>)}
                  </Select>
                </Field>
                <Field label={t("qty")} hint={form.type === "adjustment" ? "+ / −" : form.type === "damage" ? "−" : "+"}>
                  <Input inputMode="decimal" value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} />
                </Field>
              </div>
              <Field label={needsReason ? t("reason") : `${t("reason")} (${t("optional")})`}>
                <Input value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
              </Field>
              <Field label={`${t("reference")} (${t("optional")})`}>
                <Input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
              </Field>
              <ErrorText>{err}</ErrorText>
              {ok && <p className="text-sm font-medium text-emerald-700 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">✓ {ok}</p>}
              <Button className="w-full py-2.5 font-semibold" onClick={submit}
                disabled={busy || !form.product || q === null || q === 0 || (needsReason && !form.reason.trim())}>
                {t("save")}
              </Button>
            </div>
          </Card>
        )}
        <Card title={`${t("low_stock")} (${low?.length ?? 0})`} className={can("stock.write") ? "lg:col-span-2" : "lg:col-span-3"}>
          <Table head={[t("item"), t("sku"), t("in_stock"), t("low_stock_level")]} empty={low?.length === 0}>
            {low?.map((p) => (
              <tr key={p.product_id}>
                <td className={td}><span className="font-semibold text-slate-900">{name(p)}</span></td>
                <td className={td}><span className="font-mono text-xs text-slate-600">{p.sku}</span></td>
                <td className={`${tdNum} ${p.stock_milli <= 0 ? "font-bold text-red-600" : "font-semibold text-amber-700"}`}>{qty(p.stock_milli)} {tv(p.unit)}</td>
                <td className={tdNum}>{qty(p.low_stock_milli)}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>

      <Card title={t("movements")} actions={
        <div className="w-full sm:w-64">
          <Select value={productFilter} onChange={(e) => setProductFilter(e.target.value)}>
            <option value="">{t("all")}</option>
            {products?.map((p) => <option key={p.id} value={p.id}>{name(p)}</option>)}
          </Select>
        </div>
      }>
        <Table head={[t("date"), t("item"), t("type"), t("qty"), t("number"), t("reason"), t("prepared_by")]} empty={moves?.length === 0}>
          {moves?.map((m) => (
            <tr key={m.id}>
              <td className={td}><span className="text-xs sm:text-sm">{dt(m.created_at)}</span></td>
              <td className={td}><span className="font-medium text-slate-900">{m.product_name}</span></td>
              <td className={td}>{tv(m.type)}</td>
              <td className={`${tdNum} font-bold ${m.qty_milli < 0 ? "text-red-600" : "text-emerald-700"}`}>{m.qty_milli > 0 ? "+" : ""}{qty(m.qty_milli)} {tv(m.unit)}</td>
              <td className={td}>{m.document_id ? <Link className="font-medium text-brand-700 hover:underline" to={`/documents/${m.document_id}`}>{m.document_number}</Link> : <span className="text-slate-500">{m.reference || "—"}</span>}</td>
              <td className={`${td} max-w-xs truncate text-xs text-slate-600`}>{m.reason || "—"}</td>
              <td className={td}><span className="text-xs sm:text-sm">{m.user_name}</span></td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
