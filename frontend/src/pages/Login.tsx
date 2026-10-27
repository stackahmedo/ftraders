import { useState, type FormEvent } from "react";
import { Button, ErrorText, Field, Input } from "../components/ui";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";

export default function Login() {
  const { login } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-900 to-brand-700 p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-brand-900">{t("app_name")}</h1>
            <p className="text-sm text-slate-500">ERP</p>
          </div>
          <button type="button" className="rounded-md border px-2 py-1 text-xs" onClick={() => setLang(lang === "en" ? "bn" : "en")}>
            {t("language")}
          </button>
        </div>
        <Field label={t("username")}>
          <Input autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        </Field>
        <Field label={t("password")}>
          <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <ErrorText>{error}</ErrorText>
        <Button className="w-full" disabled={busy || !username || !password}>{t("login")}</Button>
      </form>
    </div>
  );
}
