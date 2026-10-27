import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
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
  const location = useLocation();
  const items = NAV.filter((n) => n.perm.some(can));

  // Lock body scroll when mobile drawer is open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Close drawer on route change
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const link = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
      isActive
        ? "bg-brand-600 text-white shadow-xs font-semibold"
        : "text-brand-50/90 hover:bg-brand-700/80 hover:text-white"
    }`;

  const nav = (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto pr-1">
      {items.map((n) => (
        <NavLink key={n.to} to={n.to} end={n.to === "/"} className={link} onClick={() => setOpen(false)}>
          <span className="w-5 text-center text-base">{n.icon}</span>
          <span className="truncate">{t(n.label)}</span>
        </NavLink>
      ))}
    </nav>
  );

  const footer = (
    <div className="mt-4 space-y-3 border-t border-brand-700/80 pt-4 text-sm text-brand-50">
      <div className="flex items-center justify-between">
        <div className="min-w-0 pr-2">
          <div className="truncate font-semibold text-white">{user?.full_name}</div>
          <div className="text-xs uppercase tracking-wider text-brand-200/80">{user?.role_name}</div>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-700 text-xs font-bold text-white">
          {user?.full_name?.charAt(0) || "U"}
        </div>
      </div>
      <div className="flex gap-2">
        <button
          className="flex-1 rounded-md bg-brand-700/80 px-2.5 py-1.5 text-xs font-medium text-white transition hover:bg-brand-600 active:scale-95"
          onClick={() => setLang(lang === "en" ? "bn" : "en")}
        >
          🌐 {t("language")}
        </button>
        <button
          className="rounded-md bg-brand-700/80 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-red-600 active:scale-95"
          onClick={logout}
        >
          {t("logout")}
        </button>
      </div>
    </div>
  );

  // Quick bottom bar items for mobile
  const hasSale = can("docs.write");
  const hasDocs = can("docs.read") || can("docs.read_own");
  const hasDash = can("dashboard.read");
  const hasStock = can("stock.read");
  const hasDues = can("payments.read");

  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col bg-brand-900 p-4 lg:sticky lg:top-0 lg:flex lg:h-screen shadow-lg">
        <div className="mb-6 flex items-center gap-2.5 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500 text-white font-bold text-lg shadow-sm">
            FR
          </div>
          <div className="min-w-0">
            <div className="truncate text-base font-bold text-white leading-tight">{t("app_name")}</div>
            <div className="text-[10px] font-medium uppercase tracking-widest text-brand-200">ERP System</div>
          </div>
        </div>
        {nav}
        {footer}
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-brand-800 bg-brand-900 px-4 py-3 text-white shadow-sm lg:hidden">
        <div className="flex items-center gap-2.5 min-w-0">
          <button
            onClick={() => setOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-800 text-lg hover:bg-brand-700 active:scale-95"
            aria-label="Open Navigation Menu"
          >
            ☰
          </button>
          <div className="min-w-0">
            <span className="block truncate font-bold text-sm sm:text-base leading-tight">{t("app_name")}</span>
            <span className="text-[10px] uppercase tracking-wider text-brand-200">{user?.role_name}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="rounded-lg bg-brand-800 px-2.5 py-1.5 text-xs font-semibold text-brand-100 hover:bg-brand-700 active:scale-95"
            onClick={() => setLang(lang === "en" ? "bn" : "en")}
          >
            {lang === "en" ? "বাং" : "EN"}
          </button>
        </div>
      </header>

      {/* Mobile drawer backdrop & sidebar */}
      {open && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs transition-opacity lg:hidden"
          onClick={() => setOpen(false)}
        >
          <aside
            className="flex h-full w-72 max-w-[85vw] flex-col bg-brand-900 p-4 shadow-2xl transition-transform animate-in slide-in-from-left duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between border-b border-brand-800 pb-3">
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 font-bold text-white">
                  FR
                </div>
                <div className="truncate font-bold text-white text-sm">{t("app_name")}</div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 text-brand-200 hover:bg-brand-800 hover:text-white"
                aria-label="Close Menu"
              >
                ✕
              </button>
            </div>
            {nav}
            {footer}
          </aside>
        </div>
      )}

      {/* Main content with safe bottom padding for mobile navigation bar */}
      <main className="mx-auto w-full max-w-7xl flex-1 p-3.5 sm:p-5 lg:p-6 pb-24 lg:pb-6">
        <Outlet />
      </main>

      {/* Mobile bottom navigation bar for quick access */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 flex items-center justify-around border-t border-slate-200 bg-white/95 px-2 py-1.5 backdrop-blur-md shadow-lg lg:hidden bottom-safe">
        {hasDash && (
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex flex-col items-center py-1 px-2 text-[11px] font-medium transition ${
                isActive ? "text-brand-600 font-semibold" : "text-slate-500 hover:text-slate-900"
              }`
            }
          >
            <span className="text-lg">▦</span>
            <span>{t("dashboard")}</span>
          </NavLink>
        )}

        {hasDocs && (
          <NavLink
            to="/documents"
            className={({ isActive }) =>
              `flex flex-col items-center py-1 px-2 text-[11px] font-medium transition ${
                isActive ? "text-brand-600 font-semibold" : "text-slate-500 hover:text-slate-900"
              }`
            }
          >
            <span className="text-lg">▤</span>
            <span>{t("documents")}</span>
          </NavLink>
        )}

        {hasSale && (
          <NavLink
            to="/sale"
            className={({ isActive }) =>
              `-mt-5 flex h-13 w-13 flex-col items-center justify-center rounded-full bg-brand-600 text-white shadow-md border-4 border-slate-50 active:scale-95 transition ${
                isActive ? "ring-2 ring-brand-400" : ""
              }`
            }
            aria-label={t("new_sale")}
          >
            <span className="text-2xl font-light leading-none">＋</span>
          </NavLink>
        )}

        {hasStock ? (
          <NavLink
            to="/stock"
            className={({ isActive }) =>
              `flex flex-col items-center py-1 px-2 text-[11px] font-medium transition ${
                isActive ? "text-brand-600 font-semibold" : "text-slate-500 hover:text-slate-900"
              }`
            }
          >
            <span className="text-lg">⇅</span>
            <span>{t("stock")}</span>
          </NavLink>
        ) : hasDues ? (
          <NavLink
            to="/dues"
            className={({ isActive }) =>
              `flex flex-col items-center py-1 px-2 text-[11px] font-medium transition ${
                isActive ? "text-brand-600 font-semibold" : "text-slate-500 hover:text-slate-900"
              }`
            }
          >
            <span className="text-lg">৳</span>
            <span>{t("due_list")}</span>
          </NavLink>
        ) : null}

        <button
          onClick={() => setOpen(true)}
          className="flex flex-col items-center py-1 px-2 text-[11px] font-medium text-slate-500 hover:text-slate-900 transition"
        >
          <span className="text-lg">☰</span>
          <span>{t("settings")}</span>
        </button>
      </nav>
    </div>
  );
}
