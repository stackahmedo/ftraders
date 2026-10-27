import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useI18n, type TKey } from "../lib/i18n";

const NAV: { to: string; label: TKey; perm: string[]; icon: string }[] = [
  { to: "/", label: "dashboard", perm: ["dashboard.read"], icon: "▦" },
  { to: "/sale", label: "new_sale", perm: ["docs.write"], icon: "＋" },
  { to: "/documents", label: "documents", perm: ["docs.read", "docs.read_own"], icon: "▤" },
  { to: "/products", label: "products", perm: ["products.read"], icon: "◫" },
  { to: "/customers", label: "customers", perm: ["customers.read"], icon: "☺" },
  { to: "/stock", label: "stock", perm: ["stock.read"], icon: "⇅" },
  { to: "/dues", label: "due_list", perm: ["payments.read"], icon: "৳" },
  { to: "/audit", label: "audit_log", perm: ["audit.read"], icon: "≣" },
  { to: "/users", label: "users", perm: ["users.read"], icon: "⚇" },
  { to: "/settings", label: "settings", perm: ["settings.read"], icon: "⚙" },
];

export default function Layout() {
  const { user, logout, can } = useAuth();
  const { t, lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const items = NAV.filter((n) => n.perm.some(can));

  const link = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
      isActive ? "bg-brand-600 text-white" : "text-brand-50/90 hover:bg-brand-700"
    }`;

  const nav = (
    <nav className="flex flex-1 flex-col gap-1">
      {items.map((n) => (
        <NavLink key={n.to} to={n.to} end={n.to === "/"} className={link} onClick={() => setOpen(false)}>
          <span className="w-5 text-center">{n.icon}</span>
          {t(n.label)}
        </NavLink>
      ))}
    </nav>
  );

  const footer = (
    <div className="mt-4 space-y-2 border-t border-brand-700 pt-4 text-sm text-brand-50">
      <div>
        <div className="font-medium">{user?.full_name}</div>
        <div className="text-xs capitalize text-brand-100/80">{user?.role_name}</div>
      </div>
      <div className="flex gap-2">
        <button className="rounded-md bg-brand-700 px-2.5 py-1 text-xs" onClick={() => setLang(lang === "en" ? "bn" : "en")}>
          {t("language")}
        </button>
        <button className="rounded-md bg-brand-700 px-2.5 py-1 text-xs" onClick={logout}>{t("logout")}</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen lg:flex">
      {/* desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col bg-brand-900 p-4 lg:sticky lg:top-0 lg:flex lg:h-screen">
        <div className="mb-6 px-2 text-lg font-bold text-white">{t("app_name")}</div>
        {nav}
        {footer}
      </aside>

      {/* mobile top bar + drawer */}
      <header className="sticky top-0 z-40 flex items-center justify-between bg-brand-900 px-4 py-3 text-white lg:hidden">
        <button onClick={() => setOpen(true)} className="text-xl" aria-label="Menu">☰</button>
        <span className="font-semibold">{t("app_name")}</span>
        <button className="rounded-md bg-brand-700 px-2 py-1 text-xs" onClick={() => setLang(lang === "en" ? "bn" : "en")}>
          {t("language")}
        </button>
      </header>
      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 lg:hidden" onClick={() => setOpen(false)}>
          <aside className="flex h-full w-64 flex-col bg-brand-900 p-4" onClick={(e) => e.stopPropagation()}>
            <div className="mb-6 px-2 text-lg font-bold text-white">{t("app_name")}</div>
            {nav}
            {footer}
          </aside>
        </div>
      )}

      <main className="mx-auto w-full max-w-7xl flex-1 p-4 lg:p-6">
        <Outlet />
      </main>
    </div>
  );
}
