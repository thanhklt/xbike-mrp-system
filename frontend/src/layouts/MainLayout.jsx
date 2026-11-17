import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, Home, LogOut, Menu, UserRound, X } from "lucide-react";
import { useAuth } from "../features/auth/AuthProvider.jsx";
import { useFeedback } from "../components/FeedbackProvider.jsx";
import { ROLE_LABELS, initials } from "../lib/format.js";
import { navigationFor } from "./navigation.js";
import { Sidebar } from "./Sidebar.jsx";
import sidebarStyles from "./Sidebar.module.css";
import "./Warehouse.css";

function adminBreadcrumbs(pathname) {
  if (pathname === "/admin/tai-khoan/moi") {
    return [{ label: "Quản lý tài khoản", to: "/admin/tai-khoan" }, { label: "Tạo tài khoản" }];
  }
  if (pathname.startsWith("/admin/tai-khoan/")) {
    return [
      { label: "Quản lý tài khoản", to: "/admin/tai-khoan" },
      { label: "Chi tiết tài khoản" },
    ];
  }
  if (pathname === "/admin/tai-khoan") return [{ label: "Quản lý tài khoản" }];
  if (pathname === "/admin/vai-tro") return [{ label: "Quản lý vai trò" }];
  if (pathname.startsWith("/admin/lich-su/")) {
    return [{ label: "Lịch sử thao tác", to: "/admin/lich-su" }, { label: "Chi tiết lịch sử" }];
  }
  if (pathname === "/admin/lich-su") return [{ label: "Lịch sử thao tác" }];
  if (pathname === "/ho-so") return [{ label: "Hồ sơ" }];
  return [{ label: "Tổng quan" }];
}

// UC-02 Đăng xuất — Main 1: cung cấp thao tác đăng xuất trong menu (specs/use_cases/identity_access/UC-02.md)
export function MainLayout() {
  const { user, logout } = useAuth();
  const { confirm } = useFeedback();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isAdmin = user.ma_vai_tro === "quan_tri_vien";
  const isWarehouse = user.ma_vai_tro === "quan_ly";
  const groups = navigationFor(user.ma_vai_tro);
  const name = user.ho_ten || user.ten_dang_nhap;
  const avatarText = initials(name);

  useEffect(() => {
    if (isAdmin) {
      document.documentElement.dataset.adminTheme = "true";
    } else {
      delete document.documentElement.dataset.adminTheme;
    }
    if (isWarehouse) document.documentElement.dataset.warehouseTheme = "true";
    else delete document.documentElement.dataset.warehouseTheme;
    return () => {
      delete document.documentElement.dataset.adminTheme;
      delete document.documentElement.dataset.warehouseTheme;
    };
  }, [isAdmin, isWarehouse]);

  // UC-02 Đăng xuất — Main 1–3, A3: hỏi xác nhận, chỉ đăng xuất khi đồng ý (specs/use_cases/identity_access/UC-02.md)
  function signOut() {
    confirm({
      title: "Đăng xuất",
      description: "Bạn có muốn kết thúc phiên làm việc?",
      hideImpact: true,
      variant: "logout",
      // UC-02 Đăng xuất — Main 2–3: xóa phiên và chuyển về đăng nhập (specs/use_cases/identity_access/UC-02.md)
      onConfirm: () => {
        logout();
        navigate("/dang-nhap", { replace: true });
      },
    });
  }

  const userMenu = (
    <details className="user-menu">
      <summary>
        <span className="avatar">{avatarText}</span>
        <span>
          <strong>{name}</strong>
          <small>{isAdmin ? "Quản trị viên hệ thống" : ROLE_LABELS[user.ma_vai_tro]}</small>
        </span>
        <ChevronDown size={18} />
      </summary>
      <div className="user-dropdown">
        <NavLink to="/ho-so">
          <UserRound size={16} /> Hồ sơ
        </NavLink>
        <button type="button" onClick={signOut}>
          <LogOut size={16} /> Đăng xuất
        </button>
      </div>
    </details>
  );

  if (isAdmin) {
    const crumbs = adminBreadcrumbs(pathname);
    return (
      <div className="app-shell admin-shell">
        <a className="skip-link" href="#main-content">
          Đến nội dung chính
        </a>
        <div className="shell-body admin-shell-body">
          <Sidebar
            groups={groups}
            mobileOpen={menuOpen}
            onNavigate={() => setMenuOpen(false)}
            adminTheme
          />
          {menuOpen && (
            <div
              className="admin-sidebar-backdrop"
              aria-hidden="true"
              onClick={() => setMenuOpen(false)}
            />
          )}
          <div className="admin-workspace">
            <header className="admin-topbar">
              <div className="admin-topbar-left">
                <button
                  type="button"
                  className="icon-button menu-toggle"
                  aria-label={menuOpen ? "Đóng điều hướng" : "Mở điều hướng"}
                  aria-expanded={menuOpen}
                  aria-controls="main-navigation"
                  onClick={() => setMenuOpen(!menuOpen)}
                >
                  {menuOpen ? <X size={22} /> : <Menu size={22} />}
                </button>
                <nav className="admin-breadcrumb" aria-label="Đường dẫn trang">
                  <Home size={18} className="admin-breadcrumb-home" aria-hidden="true" />
                  {crumbs.map((crumb, index) => (
                    <span key={crumb.label} className="admin-breadcrumb-item">
                      {index > 0 && (
                        <ChevronRight
                          size={15}
                          className="admin-breadcrumb-sep"
                          aria-hidden="true"
                        />
                      )}
                      {crumb.to ? (
                        <Link to={crumb.to}>{crumb.label}</Link>
                      ) : (
                        <span aria-current="page">{crumb.label}</span>
                      )}
                    </span>
                  ))}
                </nav>
              </div>
              {userMenu}
            </header>
            <main id="main-content" className="page-body admin-page-body" tabIndex={-1}>
              <Outlet />
            </main>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`app-shell ${sidebarStyles.layout}${isWarehouse ? " warehouse-shell" : ""}`}
      data-warehouse-page={isWarehouse ? pathname.split("/")[2] || "overview" : undefined}
    >
      <a className="skip-link" href="#main-content">
        Đến nội dung chính
      </a>
      <header className="topbar">
        <div className="topbar-left">
          <button
            type="button"
            className="icon-button menu-toggle"
            aria-label={menuOpen ? "Đóng điều hướng" : "Mở điều hướng"}
            aria-expanded={menuOpen}
            aria-controls="main-navigation"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
          {!isWarehouse && (
            <div className="brand">
              XBIKE
              <small>Hệ thống quản lý kho & sản xuất</small>
            </div>
          )}
        </div>
        {userMenu}
      </header>
      <div className="shell-body">
        <Sidebar
          groups={groups}
          mobileOpen={menuOpen}
          onNavigate={() => setMenuOpen(false)}
          warehouseTheme={isWarehouse}
        />
        <main id="main-content" className="page-body" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
