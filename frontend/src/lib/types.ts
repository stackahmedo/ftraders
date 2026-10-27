export type Role = "owner" | "manager" | "cashier" | "warehouse" | "delivery";

export interface User {
  id: number;
  username: string;
  full_name: string;
  phone: string | null;
  role_name: Role;
  is_active: boolean;
  permissions: string[];
}

export interface Product {
  id: number;
  name: string;
  name_bn: string | null;
  sku: string;
  barcode: string | null;
  category_name: string | null;
  unit: "piece" | "carton" | "kg";
  buy_price_paisa: number;
  retail_price_paisa: number;
  wholesale_price_paisa: number;
  low_stock_milli: number;
  stock_milli: number;
  is_active: boolean;
}

export type CustomerType = "retail" | "wholesale" | "credit";

export interface Customer {
  id: number;
  name: string;
  phone: string | null;
  address: string | null;
  type: CustomerType;
  credit_limit_paisa: number;
  opening_balance_paisa: number;
  notes: string | null;
  is_active: boolean;
  balance_paisa: number;
}

export type DocType = "estimate" | "delivery" | "invoice";

export interface DocSummary {
  id: number;
  doc_type: DocType;
  number: string;
  status: "open" | "converted" | "posted" | "void";
  customer_id: number | null;
  customer_name: string;
  customer_phone: string | null;
  total_paisa: number;
  paid_paisa: number;
  due_paisa: number;
  payment_status: "paid" | "partial" | "due" | "installment" | null;
  created_at: string;
  created_by_name: string;
}

export interface DocItem {
  id: number;
  line_no: number;
  product_id: number;
  description: string;
  unit: string;
  qty_milli: number;
  unit_price_paisa: number;
  discount_paisa: number;
  line_total_paisa: number;
}

export interface Payment {
  id: number;
  customer_id: number | null;
  document_id: number | null;
  amount_paisa: number;
  method: "cash" | "bkash" | "nagad" | "bank";
  reference: string | null;
  note: string | null;
  paid_at: string;
  reversal_of_id: number | null;
  user_name: string;
  document_number: string | null;
  is_reversed: boolean;
}

export interface Installment {
  id: number;
  seq: number;
  due_date: string;
  amount_paisa: number;
  paid_paisa: number;
  is_paid: boolean;
  is_overdue: boolean;
}

export interface DocDetail extends DocSummary {
  customer_address: string | null;
  price_tier: string;
  subtotal_paisa: number;
  discount_paisa: number;
  notes: string | null;
  parent_id: number | null;
  parent_number: string | null;
  children: { id: number; number: string; doc_type: DocType; status: string }[];
  moves_stock: boolean;
  assigned_to_id: number | null;
  assigned_to_name: string | null;
  approved_by_name: string | null;
  verify_token: string;
  voided_at: string | null;
  voided_by_name: string | null;
  void_reason: string | null;
  items: DocItem[];
  payments: Payment[];
  installments: Installment[];
}

export interface Movement {
  id: number;
  created_at: string;
  product_id: number;
  product_name: string;
  unit: string;
  qty_milli: number;
  type: string;
  document_id: number | null;
  document_number: string | null;
  reversal_of_id: number | null;
  reference: string | null;
  reason: string | null;
  user_name: string;
}

export interface LowStock {
  product_id: number;
  name: string;
  name_bn: string | null;
  sku: string;
  unit: string;
  stock_milli: number;
  low_stock_milli: number;
}

export type Settings = Record<string, string>;
