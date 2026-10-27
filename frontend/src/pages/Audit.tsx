import { useState } from "react";
import { Card, PageHeader, Select, Table, td } from "../components/ui";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";

interface Row {
  id: number; at: string; user_name: string | null; entity: string; entity_id: number | null;
  action: string; field: string | null; old_value: string | null; new_value: string | null; reason: string | null;
}

const ENTITIES = ["document", "payment", "product", "stock", "customer", "installment_plan", "setting", "user"];

export default function AuditPage() {
  const { t, dt } = useI18n();
  const [entity, setEntity] = useState("");
  const { data } = useApi<Row[]>(`/api/audit?limit=500${entity ? `&entity=${entity}` : ""}`);
  return (
    <div className="space-y-4">
      <PageHeader title={t("audit_log")} actions={
        <div className="w-full sm:w-56">
          <Select value={entity} onChange={(e) => setEntity(e.target.value)}>
            <option value="">{t("all")}</option>
            {ENTITIES.map((e) => <option key={e} value={e}>{e}</option>)}
          </Select>
        </div>
      } />
      <Card>
        <Table head={[t("date"), "User", "Record", "Action", "Field", "Old", "New", t("reason")]} empty={data?.length === 0}>
          {data?.map((r) => (
            <tr key={r.id}>
              <td className={td}><span className="text-xs text-slate-500 whitespace-nowrap">{dt(r.at)}</span></td>
              <td className={td}><span className="font-medium text-slate-800">{r.user_name || "—"}</span></td>
              <td className={td}><span className="font-mono text-xs">{r.entity}{r.entity_id ? ` #${r.entity_id}` : ""}</span></td>
              <td className={td}><span className="inline-block rounded px-1.5 py-0.5 text-xs font-medium bg-slate-100 text-slate-700">{r.action}</span></td>
              <td className={td}><span className="text-xs text-slate-600">{r.field || "—"}</span></td>
              <td className={`${td} text-slate-500 font-mono text-xs max-w-xs truncate`}>{r.old_value || "—"}</td>
              <td className={`${td} text-slate-800 font-mono text-xs max-w-xs truncate`}>{r.new_value || "—"}</td>
              <td className={`${td} max-w-xs truncate text-xs text-slate-600`}>{r.reason || "—"}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
