import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Card, ErrorText, PageHeader, Table, td, tdNum } from "../components/ui";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import type { CustomerType, DocSummary } from "../lib/types";

interface Dues {
  total_due_paisa: number;
  invoices: (DocSummary & { days_old: number; next_installment: { due_date: string; amount_paisa: number; is_overdue: boolean } | null })[];
  customers: { customer_id: number; name: string; phone: string | null; type: CustomerType; credit_limit_paisa: number; balance_paisa: number }[];
}

export default function DuesPage() {
  const { t, money, dt } = useI18n();
  const { data, error } = useApi<Dues>("/api/dues");
  const [tab, setTab] = useState<"customers" | "invoices">("customers");

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("due_list")}
        actions={data && (
          <div className="w-full sm:w-auto rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm font-bold text-red-700 shadow-2xs">
            {t("total_due")}: {money(data.total_due_paisa)}
          </div>
        )}
      />
      <ErrorText>{error}</ErrorText>
      <div className="flex w-full sm:w-fit rounded-lg border border-slate-300 bg-white p-0.5 shadow-2xs">
        {(["customers", "invoices"] as const).map((x) => (
          <button
            key={x}
            onClick={() => setTab(x)}
            className={`flex-1 sm:flex-initial rounded-md px-4 py-2 text-xs sm:text-sm font-medium transition ${
              tab === x ? "bg-brand-600 text-white shadow-2xs" : "text-slate-700 hover:text-slate-900"
            }`}
          >
            {t(x === "customers" ? "by_customer" : "by_invoice")}
          </button>
        ))}
      </div>
      {tab === "customers" ? (
        <Card>
          <Table head={[t("customer"), t("phone"), t("type"), t("credit_limit"), t("due")]} empty={data?.customers.length === 0}>
            {data?.customers.map((c) => (
              <tr key={c.customer_id}>
                <td className={td}><Link className="font-semibold text-brand-700 hover:underline" to={`/customers/${c.customer_id}`}>{c.name}</Link></td>
                <td className={td}>{c.phone ? <a className="text-slate-700 hover:text-brand-700" href={`tel:${c.phone}`}>{c.phone}</a> : "—"}</td>
                <td className={td}><Badge value={c.type} /></td>
                <td className={tdNum}>{money(c.credit_limit_paisa)}</td>
                <td className={`${tdNum} font-bold ${c.balance_paisa > c.credit_limit_paisa ? "text-red-700" : "text-red-600"}`}>{money(c.balance_paisa)}</td>
              </tr>
            ))}
          </Table>
        </Card>
      ) : (
        <Card>
          <Table head={[t("number"), t("customer"), t("total"), t("due"), t("days_old"), t("next_installment"), t("status")]} empty={data?.invoices.length === 0}>
            {data?.invoices.map((d) => (
              <tr key={d.id}>
                <td className={td}>
                  <Link className="font-semibold text-brand-700 hover:underline" to={`/documents/${d.id}`}>{d.number}</Link>
                  <div className="text-xs text-slate-500">{dt(d.created_at)}</div>
                </td>
                <td className={td}>
                  <div className="font-medium text-slate-900">{d.customer_name}</div>
                  {d.customer_phone && <div className="text-xs text-slate-500">{d.customer_phone}</div>}
                </td>
                <td className={tdNum}>{money(d.total_paisa)}</td>
                <td className={`${tdNum} font-bold text-red-600`}>{money(d.due_paisa)}</td>
                <td className={`${tdNum} ${d.days_old > 30 ? "font-bold text-red-600" : "text-slate-700"}`}>{d.days_old}</td>
                <td className={td}>
                  {d.next_installment ? (
                    <span className={d.next_installment.is_overdue ? "font-bold text-red-600" : "text-slate-700"}>
                      {d.next_installment.due_date} · {money(d.next_installment.amount_paisa)}{d.next_installment.is_overdue && ` · ${t("overdue")}`}
                    </span>
                  ) : "—"}
                </td>
                <td className={td}><Badge value={d.payment_status} /></td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
    </div>
  );
}
