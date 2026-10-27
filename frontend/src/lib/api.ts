export class ApiError extends Error {
  status: number;
  code?: string;
  kind?: string;
  constructor(status: number, message: string, code?: string, kind?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.kind = kind;
  }
}

const TOKEN_KEY = "erp_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

function messageFrom(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => (e && typeof e === "object" && "msg" in e ? String(e.msg) : String(e))).join("; ");
  }
  return fallback;
}

export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown; form?: Record<string, string> } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) {
    body = new URLSearchParams(opts.form);
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, { method: opts.method ?? (body ? "POST" : "GET"), headers, body });
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    const d = (data ?? {}) as { code?: string; kind?: string };
    throw new ApiError(res.status, messageFrom(data, `Request failed (${res.status})`), d.code, d.kind);
  }
  return data as T;
}

/** Open a server PDF (needs the auth header, so fetch it and open a blob URL). */
export async function openPdf(docId: number, layout: "a4" | "thermal") {
  const win = window.open("", "_blank");
  const res = await fetch(`/api/documents/${docId}/pdf?layout=${layout}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ""}` },
  });
  if (!res.ok) {
    win?.close();
    throw new ApiError(res.status, "Could not create the PDF");
  }
  const url = URL.createObjectURL(await res.blob());
  if (win) win.location.href = url;
  else window.location.href = url;
}
