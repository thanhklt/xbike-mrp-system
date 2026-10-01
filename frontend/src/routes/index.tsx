import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "@/features/auth/LoginPage";
import { UsersPage } from "@/features/auth/UsersPage";
import { BOMPage } from "@/features/bom/BOMPage";
import { FinishedGoodsPage } from "@/features/finished-goods-issuing/FinishedGoodsPage";
import { InventoryPage } from "@/features/inventory/InventoryPage";
import { MaterialIssuingPage } from "@/features/material-issuing/MaterialIssuingPage";
import { MaterialsPage } from "@/features/materials/MaterialsPage";
import { ProductionPage } from "@/features/production/ProductionPage";
import { ProductsPage } from "@/features/products/ProductsPage";
import { ReceivingPage } from "@/features/receiving/ReceivingPage";
import { AuditPage } from "@/features/reports/AuditPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { SuppliersPage } from "@/features/suppliers/SuppliersPage";
import { MainLayout } from "@/layouts/MainLayout";

export const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<MainLayout />}>
          <Route path="/" element={<ReportsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/bom" element={<BOMPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/receiving" element={<ReceivingPage />} />
          <Route path="/material-issuing" element={<MaterialIssuingPage />} />
          <Route path="/production" element={<ProductionPage />} />
          <Route path="/finished-goods-issuing" element={<FinishedGoodsPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
