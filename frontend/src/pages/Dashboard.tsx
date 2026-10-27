import { Link } from "react-router-dom";
import { Badge, Card, ErrorText, PageHeader, Table, td, tdNum } from "../components/ui";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import type { DocSummary, LowStock } from "../lib/types";

interface Dash {
  low_stock: LowStock[];
  sales_count?: number;
  sales_paisa?: number;
  collected_paisa?: number;
  due_collected_paisa?: number;
  total_due_paisa?: number;
  recent?: DocSummary[];
}

function Stat({ label, value, sub, highlight }: { label: string; value: string; sub?: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-3.5 sm:p-4 shadow-xs transition hover:shadow-sm ${highlight ? "border-brand-200 bg-brand-50/40" : "border-slate-200 bg-white"}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 truncate">{label}</div>
      <div className="mt-1 text-xl sm:text-2xl font-bold tabular-nums text-slate-900">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-slate-500 font-medium">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { t, money, qty, dt, lang } = useI18n();
  const { can } = useAuth();
  const { data, error } = useApi<Dash>("/api/dashboard");

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("dashboard")}
        actions={
          can("docs.write") && (
            <Link
              to="/sale"
              className="inline-flex w-full sm:w-auto items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 active:scale-95 transition"
            >
              ＋ {t("new_sale")}
            </Link>
          )
        }
      />
      <ErrorText>{error}</ErrorText>
      {data?.sales_paisa !== undefined && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3.5">
          <Stat label={t("todays_sales")} value={money(data.sales_paisa)} sub={`${data.sales_count} ${t("invoice")}`} highlight />
          <Stat label={t("due_collected")} value={money(data.due_collected_paisa ?? 0)} />
          <Stat label={t("collected_today")} value={money(data.collected_paisa ?? 0)} />
          <Stat label={t("total_due")} value={money(data.total_due_paisa ?? 0)} />
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={`${t("low_stock")} (${data?.low_stock.length ?? 0})`}>
          <Table head={[t("item"), t("in_stock"), t("low_stock_level")]} empty={data?.low_stock.length === 0}>
            {data?.low_stock.map((p) => (
              <tr key={p.product_id}>
                <td className={td}>
                  <div className="font-semibold text-slate-900">{lang === "bn" && p.name_bn ? p.name_bn : p.name}</div>
                  <div className="font-mono text-xs text-slate-400">{p.sku}</div>
                </td>
                <td className={`${tdNum} ${p.stock_milli <= 0 ? "font-bold text-red-600" : "font-semibold text-amber-700"}`}>{qty(p.stock_milli)} {t(p.unit as "kg")}</td>
                <td className={tdNum}>{qty(p.low_stock_milli)}</td>
              </tr>
            ))}
          </Table>
        </Card>
        {data?.recent && (
          <Card title={t("recent_documents")}>
            <Table head={[t("number"), t("customer"), t("total"), t("status")]} empty={data.recent.length === 0}>
              {data.recent.map((d) => (
                <tr key={d.id}>
                  <td className={td}>
                    <Link className="font-semibold text-brand-700 hover:underline" to={`/documents/${d.id}`}>{d.number}</Link>
                    <div className="text-xs text-slate-400">{dt(d.created_at)}</div>
                  </td>
                  <td className={td}><span className="font-medium text-slate-800">{d.customer_name}</span></td>
                  <td className={`${tdNum} font-bold text-slate-900`}>{money(d.total_paisa)}</td>
                  <td className={td}><Badge value={d.status === "void" ? "void" : d.payment_status ?? d.status} /></td>
                </tr>
              ))}
            </Table>
          </Card>
        )}
      </div>
    </div>
  );
}
