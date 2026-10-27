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

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { t, money, qty, dt, lang } = useI18n();
  const { can } = useAuth();
  const { data, error } = useApi<Dash>("/api/dashboard");

  return (
    <div className="space-y-4">
      <PageHeader title={t("dashboard")} actions={can("docs.write") && <Link to="/sale" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white">{t("new_sale")}</Link>} />
      <ErrorText>{error}</ErrorText>
      {data?.sales_paisa !== undefined && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label={t("todays_sales")} value={money(data.sales_paisa)} sub={`${data.sales_count} ${t("invoice")}`} />
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
                <td className={td}>{lang === "bn" && p.name_bn ? p.name_bn : p.name}</td>
                <td className={`${tdNum} ${p.stock_milli <= 0 ? "font-semibold text-red-600" : "text-amber-700"}`}>{qty(p.stock_milli)} {t(p.unit as "kg")}</td>
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
                  <td className={td}><Link className="font-medium text-brand-700" to={`/documents/${d.id}`}>{d.number}</Link><div className="text-xs text-slate-500">{dt(d.created_at)}</div></td>
                  <td className={td}>{d.customer_name}</td>
                  <td className={tdNum}>{money(d.total_paisa)}</td>
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
