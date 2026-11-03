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
import { ManagerLayout } from "@/features/management/ManagerLayout";
import { ReceivingScreen } from "@/features/management/ReceivingScreen";
import { RequestScreen } from "@/features/management/RequestScreen";
import { ProductionScreen } from "@/features/management/ProductionScreen";
import { ApprovalScreen } from "@/features/management/ApprovalScreen";

export const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/quan-ly/nhap-kho" replace />} />
        <Route path="/quan-ly" element={<ManagerLayout />}>
          <Route index element={<Navigate to="nhap-kho" replace />} />
          <Route path="nhap-kho" element={<ReceivingScreen />} />
          <Route path="yeu-cau-thanh-pham" element={<RequestScreen />} />
          <Route path="lenh-san-xuat" element={<ProductionScreen />} />
          <Route path="duyet-phieu-xuat" element={<ApprovalScreen />} />
        </Route>

        <Route element={<MainLayout />}>
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
