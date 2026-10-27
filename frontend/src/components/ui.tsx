import { forwardRef, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { ApiError } from "../lib/api";
import { useI18n } from "../lib/i18n";

type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 disabled:bg-brand-600/50 shadow-sm",
  secondary: "bg-white text-slate-800 border border-slate-300 hover:bg-slate-50 active:bg-slate-100 shadow-xs",
  danger: "bg-red-600 text-white hover:bg-red-700 active:bg-red-800 disabled:bg-red-600/50 shadow-sm",
  ghost: "text-slate-700 hover:bg-slate-100 active:bg-slate-200",
};

export function Button({ variant = "primary", className = "", ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100 ${VARIANTS[variant]} ${className}`}
      {...rest}
    />
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className = "", ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-500 ${className}`}
      {...rest}
    />
  );
});

export function Select({ className = "", children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-500 ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function Card({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-200/90 bg-white shadow-xs overflow-hidden ${className}`}>
      {(title || actions) && (
        <header className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 px-3.5 py-3 sm:px-4">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-3.5 sm:p-4">{children}</div>
    </section>
  );
}

export function PageHeader({ title, actions }: { title: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <h1 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl">{title}</h1>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

const BADGE: Record<string, string> = {
  paid: "bg-emerald-100 text-emerald-800 border-emerald-200",
  partial: "bg-amber-100 text-amber-800 border-amber-200",
  due: "bg-red-100 text-red-700 border-red-200",
  installment: "bg-sky-100 text-sky-800 border-sky-200",
  open: "bg-sky-100 text-sky-800 border-sky-200",
  converted: "bg-slate-100 text-slate-700 border-slate-200",
  posted: "bg-emerald-100 text-emerald-800 border-emerald-200",
  void: "bg-red-600 text-white border-red-600",
  retail: "bg-slate-100 text-slate-700 border-slate-200",
  wholesale: "bg-violet-100 text-violet-800 border-violet-200",
  credit: "bg-amber-100 text-amber-800 border-amber-200",
};

export function Badge({ value }: { value: string | null | undefined }) {
  const { tv } = useI18n();
  if (!value) return null;
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${BADGE[value] ?? "bg-slate-100 text-slate-700 border-slate-200"}`}>
      {tv(value)}
    </span>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 border border-red-200">{children}</p>;
}

export function Modal({ open, title, onClose, children, footer }: { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 backdrop-blur-xs p-0 sm:items-center sm:p-4 transition-all" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-2xl sm:max-w-lg sm:rounded-2xl transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Mobile handle indicator */}
        <div className="pt-2 sm:hidden flex justify-center">
          <div className="w-12 h-1.5 bg-slate-200 rounded-full" />
        </div>
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h3 className="font-semibold text-slate-900 text-base">{title}</h3>
          <button className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="space-y-3.5 p-4 sm:p-5">{children}</div>
        {footer && <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 bg-slate-50/50 px-4 py-3 sm:px-5">{footer}</div>}
      </div>
    </div>
  );
}

export function Table({ head, children, empty }: { head: ReactNode[]; children: ReactNode; empty?: boolean }) {
  const { t } = useI18n();
  return (
    <div className="-mx-3.5 sm:-mx-4 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/70 text-left text-xs uppercase tracking-wider text-slate-500">
            {head.map((h, i) => (
              <th key={i} className="whitespace-nowrap px-3.5 py-2.5 font-semibold sm:px-4">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
      {empty && <p className="px-4 py-8 text-center text-sm text-slate-500">{t("not_found")}</p>}
    </div>
  );
}

export const td = "whitespace-nowrap px-3.5 py-2.5 sm:px-4";
export const tdNum = "whitespace-nowrap px-3.5 py-2.5 text-right tabular-nums sm:px-4";

// ---------------------------------------------------------------- supervisor approval
export type Cred = { username: string; password: string };
export type Approvals = { discount?: Cred; credit?: Cred };

/**
 * Wraps an API call that may answer 409 approval_required. Shows a login box for a
 * Manager/Owner, then retries with the collected approvals (discount and/or credit).
 */
export function useApproval() {
  const { t } = useI18n();
  const [state, setState] = useState<{ kind: string; message: string } | null>(null);
  const [cred, setCred] = useState<Cred>({ username: "", password: "" });
  const resolver = useRef<((c: Cred | null) => void) | null>(null);

  async function run<T>(fn: (a: Approvals) => Promise<T>): Promise<T> {
    const approvals: Approvals = {};
    for (let attempt = 0; attempt < 4; attempt++) {
      try {
        return await fn(approvals);
      } catch (e) {
        if (!(e instanceof ApiError) || e.code !== "approval_required" || !e.kind) throw e;
        const c = await new Promise<Cred | null>((resolve) => {
          resolver.current = resolve;
          setCred({ username: "", password: "" });
          setState({ kind: e.kind!, message: e.message });
        });
        setState(null);
        if (!c) throw new ApiError(409, e.message, "approval_cancelled");
        approvals[e.kind as keyof Approvals] = c;
      }
    }
    throw new ApiError(409, "Approval failed");
  }

  const close = (c: Cred | null) => resolver.current?.(c);

  const modal = (
    <Modal
      open={!!state}
      title={t("approval_needed")}
      onClose={() => close(null)}
      footer={
        <>
          <Button variant="secondary" onClick={() => close(null)}>{t("cancel")}</Button>
          <Button onClick={() => close(cred)} disabled={!cred.username || !cred.password}>{t("approve")}</Button>
        </>
      }
    >
      <p className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">{state?.message}</p>
      <Field label={t("approver_username")}>
        <Input autoFocus value={cred.username} onChange={(e) => setCred({ ...cred, username: e.target.value })} />
      </Field>
      <Field label={t("password")}>
        <Input type="password" value={cred.password} onChange={(e) => setCred({ ...cred, password: e.target.value })}
          onKeyDown={(e) => e.key === "Enter" && cred.username && cred.password && close(cred)} />
      </Field>
    </Modal>
  );
  return { run, modal };
}
