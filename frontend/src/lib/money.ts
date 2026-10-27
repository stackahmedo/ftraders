// Money is integer paisa, quantity is integer milli-units. No float arithmetic on money.

const BN_DIGITS = "০১২৩৪৫৬৭৮৯";

export function bnDigits(s: string): string {
  return s.replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)]);
}

function groupThousands(n: string): string {
  return n.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export function fmtTaka(paisa: number, lang: "en" | "bn" = "en"): string {
  const sign = paisa < 0 ? "-" : "";
  const p = Math.abs(Math.trunc(paisa));
  const s = `${sign}৳${groupThousands(String(Math.floor(p / 100)))}.${String(p % 100).padStart(2, "0")}`;
  return lang === "bn" ? bnDigits(s) : s;
}

/** "1,234.5" -> 123450. Returns null if invalid or more than 2 decimals. */
export function toPaisa(input: string): number | null {
  const s = input.replace(/,/g, "").trim();
  if (!/^\d+(\.\d{0,2})?$/.test(s)) return s === "" ? 0 : null;
  const [whole, frac = ""] = s.split(".");
  return Number(whole) * 100 + Number(frac.padEnd(2, "0"));
}

/** 123450 -> "1234.50" (for input fields) */
export function paisaToInput(paisa: number): string {
  const p = Math.abs(paisa);
  return `${paisa < 0 ? "-" : ""}${Math.floor(p / 100)}.${String(p % 100).padStart(2, "0")}`;
}

/** "1.5" -> 1500 */
export function toMilli(input: string): number | null {
  const s = input.trim();
  if (!/^-?\d+(\.\d{0,3})?$/.test(s)) return null;
  const neg = s.startsWith("-");
  const [whole, frac = ""] = s.replace("-", "").split(".");
  const v = Number(whole) * 1000 + Number(frac.padEnd(3, "0"));
  return neg ? -v : v;
}

export function fmtQty(milli: number, lang: "en" | "bn" = "en"): string {
  const sign = milli < 0 ? "-" : "";
  const m = Math.abs(milli);
  const whole = Math.floor(m / 1000);
  const frac = m % 1000;
  const s = frac === 0 ? `${sign}${whole}` : `${sign}${whole}.${String(frac).padStart(3, "0").replace(/0+$/, "")}`;
  return lang === "bn" ? bnDigits(s) : s;
}

/** Same rule as the server: round half-up of price x qty / 1000. */
export function lineGross(unitPaisa: number, qtyMilli: number): number {
  const n = unitPaisa * qtyMilli;
  return Math.floor((n + 500) / 1000);
}
