import { useState } from "react";
import { Button, Card, ErrorText, Field, Input, Modal, PageHeader, Select, Table, td } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";
import type { Role, User } from "../lib/types";

const ROLES: Role[] = ["owner", "manager", "cashier", "warehouse", "delivery"];

export default function Users() {
  const { t } = useI18n();
  const { can, user: me } = useAuth();
  const { data, error, reload } = useApi<User[]>("/api/users");
  const [editing, setEditing] = useState<User | "new" | null>(null);
  const [form, setForm] = useState({ username: "", full_name: "", phone: "", password: "", role: "cashier" as Role, is_active: true });
  const [err, setErr] = useState<string | null>(null);
  const editable = can("users.write");

  function open(u: User | "new") {
    setErr(null);
    setEditing(u);
    setForm(u === "new"
      ? { username: "", full_name: "", phone: "", password: "", role: "cashier", is_active: true }
      : { username: u.username, full_name: u.full_name, phone: u.phone ?? "", password: "", role: u.role_name, is_active: u.is_active });
  }

  async function save() {
    setErr(null);
    try {
      if (editing === "new") {
        await api("/api/users", { method: "POST", body: { username: form.username, full_name: form.full_name, phone: form.phone || null, password: form.password, role: form.role } });
      } else if (editing) {
        await api(`/api/users/${editing.id}`, { method: "PATCH", body: {
          full_name: form.full_name, phone: form.phone || null, role: form.role, is_active: form.is_active,
          password: form.password || null } });
      }
      setEditing(null);
      reload();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title={t("users")} actions={editable && <Button onClick={() => open("new")}>＋ {t("new_user")}</Button>} />
      <ErrorText>{error}</ErrorText>
      <Card>
        <Table head={[t("full_name"), t("username"), t("role"), t("phone"), t("active"), ""]}>
          {data?.map((u) => (
            <tr key={u.id} className={u.is_active ? "" : "opacity-50"}>
              <td className={td}>
                <span className="font-semibold text-slate-900">{u.full_name}</span>
                {u.id === me?.id && <span className="ml-1.5 text-xs bg-brand-100 text-brand-800 font-medium px-1.5 py-0.5 rounded">You</span>}
              </td>
              <td className={td}><span className="font-mono text-xs sm:text-sm text-slate-600">@{u.username}</span></td>
              <td className={`${td} capitalize`}><span className="font-medium text-slate-800">{u.role_name}</span></td>
              <td className={td}>{u.phone || "—"}</td>
              <td className={td}>{u.is_active ? <span className="text-emerald-600 font-bold">✓</span> : <span className="text-red-500 font-bold">✕</span>}</td>
              <td className={td}>{editable && <button className="text-sm font-medium text-brand-700 hover:underline" onClick={() => open(u)}>{t("edit")}</button>}</td>
            </tr>
          ))}
        </Table>
      </Card>
      <Modal open={editing !== null} title={editing === "new" ? t("new_user") : t("edit")} onClose={() => setEditing(null)}
        footer={<><Button variant="secondary" onClick={() => setEditing(null)}>{t("cancel")}</Button>
          <Button disabled={!form.full_name || (editing === "new" && (!form.username || form.password.length < 6))} onClick={save}>{t("save")}</Button></>}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label={t("username")}><Input autoFocus disabled={editing !== "new"} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
          <Field label={t("full_name")}><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
          <Field label={t("phone")}><Input inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <Field label={t("role")}>
            <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
              {ROLES.map((r) => <option key={r} value={r} className="capitalize">{r}</option>)}
            </Select>
          </Field>
        </div>
        <Field label={t("password")} hint={editing !== "new" ? "Leave blank to keep the current password" : "At least 6 characters"}>
          <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        {editing !== "new" && (
          <label className="flex items-center gap-2 text-sm text-slate-700 pt-1">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" /> {t("active")}
          </label>
        )}
        <ErrorText>{err}</ErrorText>
      </Modal>
    </div>
  );
}
