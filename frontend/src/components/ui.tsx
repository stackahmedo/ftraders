import { forwardRef, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { ApiError } from "../lib/api";
import { useI18n } from "../lib/i18n";

type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-600/50",
  secondary: "bg-white text-slate-800 border border-slate-300 hover:bg-slate-50",
  danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-600/50",
  ghost: "text-slate-700 hover:bg-slate-100",
};

export function Button({ variant = "primary", className = "", ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
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
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 ${className}`}
      {...rest}
    />
  );
});

export function Select({ className = "", children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 ${className}`}
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
    <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          <div className="flex flex-wrap gap-2">{actions}</div>
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function PageHeader({ title, actions }: { title: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      <div className="flex flex-wrap gap-2">{actions}</div>
    </div>
  );
}

const BADGE: Record<string, string> = {
  paid: "bg-emerald-100 text-emerald-800", partial: "bg-amber-100 text-amber-800",
  due: "bg-red-100 text-red-700", installment: "bg-sky-100 text-sky-800",
  open: "bg-sky-100 text-sky-800", converted: "bg-slate-100 text-slate-700",
  posted: "bg-emerald-100 text-emerald-800", void: "bg-red-600 text-white",
  retail: "bg-slate-100 text-slate-700", wholesale: "bg-violet-100 text-violet-800", credit: "bg-amber-100 text-amber-800",
};

export function Badge({ value }: { value: string | null | undefined }) {
  const { tv } = useI18n();
  if (!value) return null;
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${BADGE[value] ?? "bg-slate-100 text-slate-700"}`}>{tv(value)}</span>;
}

export function ErrorText({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{children}</p>;
}

export function Modal({ open, title, onClose, children, footer }: { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white shadow-xl sm:max-w-lg sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h3 className="font-semibold">{title}</h3>
          <button className="rounded p-1 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="space-y-3 p-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-slate-100 px-4 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Table({ head, children, empty }: { head: ReactNode[]; children: ReactNode; empty?: boolean }) {
  const { t } = useI18n();
  return (
    <div className="-mx-4 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            {head.map((h, i) => (
              <th key={i} className="whitespace-nowrap px-4 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
      {empty && <p className="px-4 py-6 text-center text-sm text-slate-500">{t("not_found")}</p>}
    </div>
  );
}

export const td = "whitespace-nowrap px-4 py-2";
export const tdNum = "whitespace-nowrap px-4 py-2 text-right tabular-nums";

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
      <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{state?.message}</p>
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
