import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { fmtQty, fmtTaka } from "./money";

const en = {
  app_name: "F Rahman Traders",
  login: "Log in", logout: "Log out", username: "Username", password: "Password",
  dashboard: "Dashboard", new_sale: "New Sale", documents: "Documents", products: "Products",
  customers: "Customers", stock: "Stock", due_list: "Due List", settings: "Settings", users: "Users",
  todays_sales: "Today's sales", due_collected: "Due collected today", collected_today: "Collected today",
  total_due: "Total due", low_stock: "Low stock", recent_documents: "Recent documents",
  search_product: "Search product or scan barcode", search: "Search", customer: "Customer",
  walk_in: "Walk-in customer", choose_customer: "Choose customer", item: "Item", qty: "Qty",
  unit: "Unit", rate: "Rate", discount: "Discount", amount: "Amount", subtotal: "Subtotal",
  total: "Total", paid: "Paid", due: "Due", pay_full: "Full", method: "Method", reference: "Reference / TrxID",
  notes: "Notes", save: "Save", cancel: "Cancel", create: "Create", edit: "Edit", add: "Add",
  estimate: "Estimate", delivery: "Delivery Challan", invoice: "Invoice",
  type: "Type", status: "Status", number: "No.", date: "Date", all: "All", actions: "Actions",
  open: "Open", converted: "Converted", posted: "Posted", void: "Void",
  status_paid: "Paid", status_partial: "Partial", status_due: "Due", status_installment: "Installment",
  cash: "Cash", bkash: "bKash", nagad: "Nagad", bank: "Bank",
  retail: "Retail", wholesale: "Wholesale", credit: "Credit",
  piece: "piece", carton: "carton", kg: "kg",
  print_a4: "Print A4", print_thermal: "Print 80mm", convert_to: "Convert to",
  add_payment: "Add payment", reverse: "Reverse", void_document: "Void document", reason: "Reason",
  installments: "Installments", make_plan: "Make installment plan", count: "Count",
  first_due: "First due date", every_days: "Every (days)", due_date: "Due date",
  overdue: "Overdue", prepared_by: "Prepared by", approved_by: "Approved by", voided_by: "Voided by",
  assigned_to: "Delivery person", none: "None", ledger: "Ledger", balance: "Balance",
  credit_limit: "Credit limit", opening_balance: "Opening balance", phone: "Phone", address: "Address",
  name: "Name", name_bn: "Name (Bangla)", sku: "SKU", barcode: "Barcode", category: "Category",
  buy_price: "Buy price", retail_price: "Retail price", wholesale_price: "Wholesale price",
  low_stock_level: "Low-stock level", in_stock: "In stock", active: "Active",
  stock_in: "Stock in", sale: "Sale", return: "Return", adjustment: "Adjustment", damage: "Damage",
  void_reversal: "Void reversal", movements: "Stock ledger", record_movement: "Record movement",
  debit: "Debit", credit_col: "Credit", receive_payment: "Receive payment",
  approval_needed: "Approval needed", approver_username: "Approver username",
  approve: "Approve", business_info: "Business info", numbering: "Numbering", thresholds: "Rules",
  allow_negative_stock: "Allow negative stock (Owner only)", discount_limit: "Discount above this % needs approval",
  role: "Role", new_user: "New user", full_name: "Full name", verify_title: "Document verification",
  verified: "This document is genuine.", not_found: "Not found", loading: "Loading…",
  no_items: "No items yet. Search a product above.", change: "Change", tendered: "Cash received",
  created: "Created", saved: "Saved", by_customer: "By customer", by_invoice: "By invoice",
  next_installment: "Next installment", days_old: "Days", audit_log: "Audit log", source: "From",
  made_from_this: "Made from this", price_tier: "Price tier", items: "Items",
  language: "বাংলা", optional: "optional",
};

type Dict = typeof en;
export type TKey = keyof Dict;

const bn: Dict = {
  app_name: "এফ রহমান ট্রেডার্স",
  login: "লগ ইন", logout: "লগ আউট", username: "ইউজারনেম", password: "পাসওয়ার্ড",
  dashboard: "ড্যাশবোর্ড", new_sale: "নতুন বিক্রি", documents: "ডকুমেন্ট", products: "পণ্য",
  customers: "ক্রেতা", stock: "স্টক", due_list: "বাকির তালিকা", settings: "সেটিংস", users: "ইউজার",
  todays_sales: "আজকের বিক্রি", due_collected: "আজ বাকি আদায়", collected_today: "আজ মোট আদায়",
  total_due: "মোট বাকি", low_stock: "স্টক কম", recent_documents: "সাম্প্রতিক ডকুমেন্ট",
  search_product: "পণ্য খুঁজুন বা বারকোড স্ক্যান করুন", search: "খুঁজুন", customer: "ক্রেতা",
  walk_in: "সাধারণ ক্রেতা", choose_customer: "ক্রেতা বাছাই করুন", item: "পণ্য", qty: "পরিমাণ",
  unit: "একক", rate: "দর", discount: "ছাড়", amount: "টাকা", subtotal: "উপমোট",
  total: "মোট", paid: "পরিশোধ", due: "বাকি", pay_full: "পুরো", method: "মাধ্যম", reference: "রেফারেন্স / TrxID",
  notes: "নোট", save: "সংরক্ষণ", cancel: "বাতিল", create: "তৈরি করুন", edit: "সম্পাদনা", add: "যোগ করুন",
  estimate: "এস্টিমেট", delivery: "ডেলিভারি চালান", invoice: "ইনভয়েস",
  type: "ধরন", status: "অবস্থা", number: "নং", date: "তারিখ", all: "সব", actions: "কাজ",
  open: "খোলা", converted: "রূপান্তরিত", posted: "পোস্টেড", void: "বাতিল (Void)",
  status_paid: "পরিশোধিত", status_partial: "আংশিক", status_due: "বাকি", status_installment: "কিস্তি",
  cash: "নগদ", bkash: "বিকাশ", nagad: "নগদ (Nagad)", bank: "ব্যাংক",
  retail: "খুচরা", wholesale: "পাইকারি", credit: "বাকি/কিস্তি",
  piece: "পিস", carton: "কার্টন", kg: "কেজি",
  print_a4: "A4 প্রিন্ট", print_thermal: "৮০মিমি প্রিন্ট", convert_to: "রূপান্তর",
  add_payment: "টাকা জমা", reverse: "ফেরত (Reverse)", void_document: "ডকুমেন্ট বাতিল", reason: "কারণ",
  installments: "কিস্তি", make_plan: "কিস্তির পরিকল্পনা", count: "সংখ্যা",
  first_due: "প্রথম কিস্তির তারিখ", every_days: "প্রতি (দিন)", due_date: "নির্ধারিত তারিখ",
  overdue: "মেয়াদোত্তীর্ণ", prepared_by: "প্রস্তুতকারী", approved_by: "অনুমোদনকারী", voided_by: "বাতিলকারী",
  assigned_to: "ডেলিভারি কর্মী", none: "কেউ না", ledger: "খতিয়ান", balance: "ব্যালেন্স",
  credit_limit: "বাকির সীমা", opening_balance: "পূর্বের বাকি", phone: "ফোন", address: "ঠিকানা",
  name: "নাম", name_bn: "নাম (বাংলা)", sku: "SKU", barcode: "বারকোড", category: "ক্যাটাগরি",
  buy_price: "ক্রয়মূল্য", retail_price: "খুচরা মূল্য", wholesale_price: "পাইকারি মূল্য",
  low_stock_level: "সর্বনিম্ন স্টক", in_stock: "স্টকে আছে", active: "সক্রিয়",
  stock_in: "স্টক ইন", sale: "বিক্রি", return: "ফেরত", adjustment: "সমন্বয়", damage: "নষ্ট",
  void_reversal: "বাতিলের সমন্বয়", movements: "স্টক খতিয়ান", record_movement: "স্টক এন্ট্রি",
  debit: "ডেবিট", credit_col: "ক্রেডিট", receive_payment: "টাকা গ্রহণ",
  approval_needed: "অনুমোদন প্রয়োজন", approver_username: "অনুমোদনকারীর ইউজারনেম",
  approve: "অনুমোদন", business_info: "ব্যবসার তথ্য", numbering: "নম্বর সিরিজ", thresholds: "নিয়ম",
  allow_negative_stock: "নেগেটিভ স্টক অনুমতি (শুধু মালিক)", discount_limit: "এই % এর বেশি ছাড়ে অনুমোদন লাগবে",
  role: "ভূমিকা", new_user: "নতুন ইউজার", full_name: "পূর্ণ নাম", verify_title: "ডকুমেন্ট যাচাই",
  verified: "এই ডকুমেন্টটি সঠিক।", not_found: "পাওয়া যায়নি", loading: "লোড হচ্ছে…",
  no_items: "এখনো কোনো পণ্য নেই। উপরে পণ্য খুঁজুন।", change: "ফেরত", tendered: "নগদ গ্রহণ",
  created: "তৈরি", saved: "সংরক্ষিত", by_customer: "ক্রেতা অনুযায়ী", by_invoice: "ইনভয়েস অনুযায়ী",
  next_installment: "পরবর্তী কিস্তি", days_old: "দিন", audit_log: "অডিট লগ", source: "উৎস",
  made_from_this: "এখান থেকে তৈরি", price_tier: "মূল্য স্তর", items: "পণ্যসমূহ",
  language: "English", optional: "ঐচ্ছিক",
};

const DICTS = { en, bn };
export type Lang = keyof typeof DICTS;

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: TKey) => string;
  /** translate an enum-like value if a key exists, else return it unchanged */
  tv: (v: string | null | undefined) => string;
  money: (paisa: number) => string;
  qty: (milli: number) => string;
  dt: (iso: string) => string;
}

const Ctx = createContext<I18n | null>(null);

function initialLang(): Lang {
  try {
    return localStorage.getItem("erp_lang") === "bn" ? "bn" : "en";
  } catch {
    return "en";
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("erp_lang", l);
    } catch {
      /* ignore */
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const dict = DICTS[lang];
  const value: I18n = {
    lang,
    setLang,
    t: (k) => dict[k] ?? en[k] ?? k,
    tv: (v) => {
      if (!v) return "";
      const key = (v in dict ? v : `status_${v}`) as TKey;
      return dict[key] ?? v;
    },
    money: (p) => fmtTaka(p, lang),
    qty: (m) => fmtQty(m, lang),
    dt: (iso) =>
      new Date(iso).toLocaleString(lang === "bn" ? "bn-BD" : "en-GB", {
        timeZone: "Asia/Dhaka", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
      }),
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const v = useContext(Ctx);
  if (!v) throw new Error("useI18n outside provider");
  return v;
}
