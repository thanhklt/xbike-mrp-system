import { Link, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "../features/auth/AuthProvider.jsx";
import { homeFor, isAllowed } from "../features/auth/permissions.js";
import { LoginPage } from "../features/auth/LoginPage.jsx";
import { UsersPage } from "../features/auth/UsersPage.jsx";
import { RolesPage } from "../features/auth/RolesPage.jsx";
import { ProfilePage } from "../features/auth/ProfilePage.jsx";
import { DashboardPage } from "../features/dashboard/DashboardPage.jsx";
import { MaterialsPage } from "../features/materials/MaterialsPage.jsx";
import { SuppliersPage } from "../features/suppliers/SuppliersPage.jsx";
import { BOMPage } from "../features/bom/BOMPage.jsx";
import { ReceivingPage } from "../features/receiving/ReceivingPage.jsx";
import { MaterialIssuingPage } from "../features/material-issuing/MaterialIssuingPage.jsx";
import { ProductionPage } from "../features/production/ProductionPage.jsx";
import { RequestsPage } from "../features/production/RequestsPage.jsx";
import { CompletionsPage } from "../features/production/CompletionsPage.jsx";
import { MyDocumentsPage } from "../features/production/MyDocumentsPage.jsx";
import { AdjustmentsPage } from "../features/inventory-adjustments/AdjustmentsPage.jsx";
import { TicketsPage } from "../features/adjustment-tickets/TicketsPage.jsx";
import { MovementsPage } from "../features/inventory/MovementsPage.jsx";
import { AuditPage } from "../features/reports/AuditPage.jsx";
import { ReportsPage } from "../features/reports/ReportsPage.jsx";
import { MainLayout } from "../layouts/MainLayout.jsx";
import { Card } from "../components/Card.jsx";
import { Button } from "../components/Button.jsx";
import { ErrorNotice } from "../components/QueryState.jsx";

function Protected() {
  const { token, user, session, logout } = useAuth();
  if (!token) return <Navigate to="/dang-nhap" replace />;
  if (!user && session.isPending)
    return (
      <div className="status-page" role="status">
        Đang kiểm tra phiên đăng nhập…
      </div>
    );
  if (session.isError)
    return (
      <div className="status-page">
        <Card title="Chưa xác minh được phiên đăng nhập">
          <div className="stack">
            <ErrorNotice error={session.error} />
            <div className="actions">
              <Button onClick={() => session.refetch()}>Thử lại</Button>
              <Button variant="secondary" onClick={() => logout()}>
                Về đăng nhập
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  return user ? <Outlet /> : <Navigate to="/dang-nhap" replace />;
}
function RoleGate({ roles }) {
  const { user } = useAuth();
  return isAllowed(user.ma_vai_tro, roles) ? <Outlet /> : <Navigate to="/403" replace />;
}
function Home() {
  const { user } = useAuth();
  return <Navigate to={homeFor(user.ma_vai_tro)} replace />;
}
function StatusPage({ code }) {
  const { user } = useAuth();
  return (
    <div className="status-page">
      <Card>
        <div className="stack">
          <span className="status-code">{code}</span>
          <h1>{code === 403 ? "Không có quyền truy cập" : "Không tìm thấy trang"}</h1>
          <p className="muted">
            {code === 403
              ? "Vai trò hiện tại không được phép truy cập chức năng này. Liên hệ quản trị viên nếu cần hỗ trợ."
              : "Đường dẫn không tồn tại hoặc đã thay đổi."}
          </p>
          <Link className="btn btn-primary" to={user ? homeFor(user.ma_vai_tro) : "/dang-nhap"}>
            Về trang chủ
          </Link>
        </div>
      </Card>
    </div>
  );
}
export function AppRoutes() {
  return (
    <>
      <Routes>
        <Route path="/dang-nhap" element={<LoginPage />} />
        <Route path="/login" element={<Navigate to="/dang-nhap" replace />} />
        <Route path="/403" element={<StatusPage code={403} />} />
        <Route path="/404" element={<StatusPage code={404} />} />
        <Route element={<Protected />}>
          <Route element={<MainLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/ho-so" element={<ProfilePage />} />
            <Route element={<RoleGate roles={["quan_tri_vien"]} />}>
              <Route path="/admin" element={<DashboardPage />} />
              <Route path="/admin/tai-khoan/:id?" element={<UsersPage />} />
              <Route path="/admin/vai-tro" element={<RolesPage />} />
              <Route path="/admin/lich-su" element={<AuditPage />} />
            </Route>
            <Route element={<RoleGate roles={["quan_ly"]} />}>
              <Route path="/kho" element={<DashboardPage />} />
              <Route path="/kho/mat-hang/:id?" element={<MaterialsPage />} />
              <Route path="/kho/nha-cung-cap/:id?" element={<SuppliersPage />} />
              <Route path="/kho/bom/:id?" element={<BOMPage />} />
              <Route path="/kho/phieu-nhap/:id?" element={<ReceivingPage />} />
              <Route path="/kho/phieu-xuat/:id?" element={<MaterialIssuingPage />} />
              <Route path="/kho/duyet-xuat/:id?" element={<MaterialIssuingPage />} />
              <Route path="/kho/yeu-cau/:id?" element={<RequestsPage />} />
              <Route path="/kho/lenh-sx/:id?" element={<ProductionPage />} />
              <Route path="/kho/duyet-hoan-thanh/:id?" element={<CompletionsPage />} />
              <Route path="/kho/dieu-chinh/:id?" element={<AdjustmentsPage />} />
              <Route path="/kho/ticket/:id?" element={<TicketsPage />} />
              <Route path="/kho/giao-dich" element={<MovementsPage />} />
              <Route path="/kho/thong-ke" element={<ReportsPage />} />
              <Route path="/kho/lich-su" element={<AuditPage />} />
            </Route>
            <Route element={<RoleGate roles={["nhan_vien"]} />}>
              <Route path="/nv" element={<DashboardPage />} />
              <Route path="/nv/yeu-cau/:id?" element={<RequestsPage />} />
              <Route path="/nv/lenh-sx/:id?" element={<ProductionPage />} />
              <Route
                path="/nv/xuat-nvl/:id?"
                element={<MaterialIssuingPage issueType="xuat_vat_tu" />}
              />
              <Route
                path="/nv/xuat-tp/:id?"
                element={<MaterialIssuingPage issueType="xuat_thanh_pham" />}
              />
              <Route path="/nv/hoan-thanh/:id?" element={<CompletionsPage />} />
              <Route path="/nv/phieu" element={<MyDocumentsPage />} />
              <Route path="/nv/ton-kho/:id?" element={<MaterialsPage readOnly />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<StatusPage code={404} />} />
      </Routes>
    </>
  );
}
