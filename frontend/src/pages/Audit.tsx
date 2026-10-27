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
        <Select className="w-48" value={entity} onChange={(e) => setEntity(e.target.value)}>
          <option value="">{t("all")}</option>
          {ENTITIES.map((e) => <option key={e} value={e}>{e}</option>)}
        </Select>
      } />
      <Card>
        <Table head={[t("date"), "User", "Record", "Action", "Field", "Old", "New", t("reason")]} empty={data?.length === 0}>
          {data?.map((r) => (
            <tr key={r.id}>
              <td className={td}>{dt(r.at)}</td>
              <td className={td}>{r.user_name}</td>
              <td className={td}>{r.entity}{r.entity_id ? ` #${r.entity_id}` : ""}</td>
              <td className={td}>{r.action}</td>
              <td className={td}>{r.field}</td>
              <td className={`${td} text-slate-500`}>{r.old_value}</td>
              <td className={td}>{r.new_value}</td>
              <td className={`${td} max-w-xs truncate`}>{r.reason}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
