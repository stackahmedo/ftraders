import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Card, ErrorText, Input, PageHeader, Select, Table, td, tdNum } from "../components/ui";
import { useApi, useDebounced } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import type { DocSummary } from "../lib/types";

export default function Documents() {
  const { t, money, dt } = useI18n();
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [pstatus, setPstatus] = useState("");
  const [q, setQ] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const dq = useDebounced(q);
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (status) params.set("status", status);
  if (pstatus) params.set("payment_status", pstatus);
  if (dq) params.set("q", dq);
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  const { data, error, loading } = useApi<DocSummary[]>(`/api/documents?${params}`);

  return (
    <div className="space-y-4">
      <PageHeader title={t("documents")} />
      <Card>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2.5">
          <div className="sm:col-span-2">
            <Input placeholder={`${t("search")}: ${t("number")}, ${t("customer")}, ${t("phone")}`} value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div>
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">{t("type")}: {t("all")}</option>
              <option value="invoice">{t("invoice")}</option>
              <option value="delivery">{t("delivery")}</option>
              <option value="estimate">{t("estimate")}</option>
            </Select>
          </div>
          <div>
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">{t("status")}: {t("all")}</option>
              {["open", "converted", "posted", "void"].map((s) => <option key={s} value={s}>{t(s as "open")}</option>)}
            </Select>
          </div>
          <div>
            <Select value={pstatus} onChange={(e) => setPstatus(e.target.value)}>
              <option value="">{t("paid")}/{t("due")}: {t("all")}</option>
              {["paid", "partial", "due", "installment"].map((s) => <option key={s} value={s}>{t(`status_${s}` as "status_paid")}</option>)}
            </Select>
          </div>
          <div className="sm:col-span-2 lg:col-span-1 grid grid-cols-2 gap-1.5">
            <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} aria-label="From" />
            <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} aria-label="To" />
          </div>
        </div>
      </Card>
      <ErrorText>{error}</ErrorText>
      <Card>
        <Table head={[t("number"), t("date"), t("customer"), t("total"), t("paid"), t("due"), t("status"), t("prepared_by")]}
          empty={!loading && data?.length === 0}>
          {data?.map((d) => (
            <tr key={d.id} className={d.status === "void" ? "opacity-60" : ""}>
              <td className={td}>
                <Link className="font-semibold text-brand-700 hover:underline" to={`/documents/${d.id}`}>{d.number}</Link>
                <div className="text-xs text-slate-500 capitalize">{t(d.doc_type)}</div>
              </td>
              <td className={td}><span className="text-xs sm:text-sm">{dt(d.created_at)}</span></td>
              <td className={td}>
                <div className="font-medium text-slate-900">{d.customer_name}</div>
                {d.customer_phone && <div className="text-xs text-slate-500">{d.customer_phone}</div>}
              </td>
              <td className={tdNum}>{money(d.total_paisa)}</td>
              <td className={tdNum}>{d.doc_type === "invoice" ? money(d.paid_paisa) : "—"}</td>
              <td className={`${tdNum} ${d.due_paisa > 0 ? "font-bold text-red-600" : ""}`}>{d.doc_type === "invoice" ? money(d.due_paisa) : "—"}</td>
              <td className={td}><div className="flex flex-wrap gap-1"><Badge value={d.status} />{d.status !== "void" && <Badge value={d.payment_status} />}</div></td>
              <td className={td}><span className="text-xs sm:text-sm text-slate-600">{d.created_by_name}</span></td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
