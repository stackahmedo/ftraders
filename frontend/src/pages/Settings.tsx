import { useEffect, useState } from "react";
import { Button, Card, ErrorText, Field, Input, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { useI18n, type TKey } from "../lib/i18n";
import type { Settings } from "../lib/types";

const BUSINESS: [string, string][] = [
  ["business_name", "Business name"], ["business_name_bn", "Business name (Bangla)"], ["address", "Address"],
  ["phone", "Phone"], ["mobile", "Mobile"], ["email", "Email"], ["website", "Website"], ["receipt_footer", "Receipt footer"],
];
const NUMBERING: [string, string][] = [
  ["prefix_estimate", "Estimate prefix"], ["next_estimate", "Next estimate no."],
  ["prefix_delivery", "Challan prefix"], ["next_delivery", "Next challan no."],
  ["prefix_invoice", "Invoice prefix"], ["next_invoice", "Next invoice no."], ["number_padding", "Digits (e.g. 4 → 0001)"],
];

export default function SettingsPage() {
  const { t } = useI18n();
  const { can } = useAuth();
  const { data, reload } = useApi<Settings>("/api/settings");
  const [form, setForm] = useState<Settings>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const editable = can("settings.write");

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  async function save() {
    setErr(null);
    setMsg(null);
    const changes = Object.fromEntries(Object.entries(form).filter(([k, v]) => data?.[k] !== v));
    try {
      await api("/api/settings", { method: "PUT", body: changes });
      setMsg(t("saved"));
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  const input = ([key, label]: [string, string]) => (
    <Field key={key} label={label}>
      <Input disabled={!editable} value={form[key] ?? ""} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
    </Field>
  );

  return (
    <div className="space-y-4">
      <PageHeader title={t("settings")} actions={editable && <Button onClick={save}>{t("save")}</Button>} />
      {msg && <p className="text-sm text-emerald-700">{msg}</p>}
      <ErrorText>{err}</ErrorText>
      <Card title={t("business_info")}><div className="grid gap-3 sm:grid-cols-2">{BUSINESS.map(input)}</div></Card>
      <Card title={t("numbering")}><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{NUMBERING.map(input)}</div></Card>
      <Card title={t("thresholds")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t("discount_limit" as TKey)}>
            <Input disabled={!editable} inputMode="decimal" value={form.discount_approval_percent ?? ""}
              onChange={(e) => setForm({ ...form, discount_approval_percent: e.target.value })} />
          </Field>
          <label className="flex items-center gap-2 self-end pb-2 text-sm">
            <input type="checkbox" disabled={!editable} checked={form.allow_negative_stock === "true"}
              onChange={(e) => setForm({ ...form, allow_negative_stock: e.target.checked ? "true" : "false" })} />
            {t("allow_negative_stock")}
          </label>
        </div>
      </Card>
    </div>
  );
}
