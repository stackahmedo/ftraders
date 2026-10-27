import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import "./index.css";
import { AuthProvider, useAuth } from "./lib/auth";
import { I18nProvider } from "./lib/i18n";
import AuditPage from "./pages/Audit";
import CustomerLedger from "./pages/CustomerLedger";
import Customers from "./pages/Customers";
import Dashboard from "./pages/Dashboard";
import DocumentDetail from "./pages/DocumentDetail";
import Documents from "./pages/Documents";
import Dues from "./pages/Dues";
import Login from "./pages/Login";
import NewSale from "./pages/NewSale";
import Products from "./pages/Products";
import SettingsPage from "./pages/Settings";
import Stock from "./pages/Stock";
import Users from "./pages/Users";
import Verify from "./pages/Verify";

function Home() {
  const { can } = useAuth();
  if (can("dashboard.read")) return <Dashboard />;
  return <Navigate to="/documents" replace />;
}

function Protected() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-8 text-slate-500">…</div>;
  if (!user) return <Login />;
  return <Layout />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/verify/:token" element={<Verify />} />
            <Route element={<Protected />}>
              <Route index element={<Home />} />
              <Route path="sale" element={<NewSale />} />
              <Route path="documents" element={<Documents />} />
              <Route path="documents/:id" element={<DocumentDetail />} />
              <Route path="products" element={<Products />} />
              <Route path="customers" element={<Customers />} />
              <Route path="customers/:id" element={<CustomerLedger />} />
              <Route path="stock" element={<Stock />} />
              <Route path="dues" element={<Dues />} />
              <Route path="audit" element={<AuditPage />} />
              <Route path="users" element={<Users />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  </React.StrictMode>,
);
