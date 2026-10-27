import { useParams } from "react-router-dom";
import { useApi } from "../lib/hooks";
import { useI18n } from "../lib/i18n";

interface V {
  business_name: string; doc_type: "estimate" | "delivery" | "invoice"; number: string; status: string;
  customer_name: string; total_paisa: number; paid_paisa: number; due_paisa: number; created_at: string; created_by_name: string;
}

/** Public page opened from the QR code. No login. */
export default function Verify() {
  const { token } = useParams();
  const { t, money, dt, tv, lang, setLang } = useI18n();
  const { data, error } = useApi<V>(`/api/public/verify/${token}`);
  const isVoid = data?.status === "void";

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="font-semibold">{t("verify_title")}</h1>
          <button className="rounded border px-2 py-0.5 text-xs" onClick={() => setLang(lang === "en" ? "bn" : "en")}>{t("language")}</button>
        </div>
        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">✕ {t("not_found")}</p>}
        {data && (
          <>
            <p className={`mb-4 rounded-lg p-3 text-sm font-medium ${isVoid ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-800"}`}>
              {isVoid ? `✕ ${t("void")}` : `✓ ${t("verified")}`}
            </p>
            <dl className="space-y-2 text-sm">
              <Row k={data.business_name} v="" />
              <Row k={t(data.doc_type)} v={data.number} />
              <Row k={t("date")} v={dt(data.created_at)} />
              <Row k={t("customer")} v={data.customer_name} />
              {data.doc_type !== "delivery" && <Row k={t("total")} v={money(data.total_paisa)} />}
              {data.doc_type === "invoice" && <><Row k={t("paid")} v={money(data.paid_paisa)} /><Row k={t("due")} v={money(data.due_paisa)} /></>}
              <Row k={t("status")} v={tv(data.status)} />
              <Row k={t("prepared_by")} v={data.created_by_name} />
            </dl>
          </>
        )}
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between gap-4 border-b border-slate-100 pb-1"><dt className="text-slate-500">{k}</dt><dd className="text-right font-medium">{v}</dd></div>;
}
