import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, Home, LogOut, Menu, UserRound, X } from "lucide-react";
import { useAuth } from "../features/auth/AuthProvider.jsx";
import { useFeedback } from "../components/FeedbackProvider.jsx";
import { ROLE_LABELS, initials } from "../lib/format.js";
import { navigationFor } from "./navigation.js";
import { Sidebar } from "./Sidebar.jsx";

function adminBreadcrumbs(pathname) {
  if (pathname === "/admin/tai-khoan/moi") {
    return [
      { label: "Quản lý tài khoản", to: "/admin/tai-khoan" },
      { label: "Tạo tài khoản" },
    ];
  }
  if (pathname.startsWith("/admin/tai-khoan/")) {
    return [
      { label: "Quản lý tài khoản", to: "/admin/tai-khoan" },
      { label: "Chi tiết tài khoản" },
    ];
  }
  if (pathname === "/admin/tai-khoan") return [{ label: "Quản lý tài khoản" }];
  if (pathname === "/admin/vai-tro") return [{ label: "Quản lý vai trò" }];
  if (pathname === "/admin/lich-su") return [{ label: "Lịch sử thao tác" }];
  if (pathname === "/ho-so") return [{ label: "Hồ sơ & đổi mật khẩu" }];
  return [{ label: "Tổng quan" }];
}

function employeeBreadcrumbs(pathname) {
  if (pathname === "/nv/yeu-cau") return [{ label: "Yêu cầu sản xuất" }];
  if (pathname.startsWith("/nv/yeu-cau/")) {
    return [
      { label: "Yêu cầu sản xuất", to: "/nv/yeu-cau" },
      { label: "Chi tiết yêu cầu" },
    ];
  }
  if (pathname === "/nv/lenh-sx") return [{ label: "Lệnh sản xuất" }];
  if (pathname.startsWith("/nv/lenh-sx/")) {
    return [
      { label: "Lệnh sản xuất", to: "/nv/lenh-sx" },
      { label: "Chi tiết lệnh" },
    ];
  }
  if (pathname === "/nv/hoan-thanh") return [{ label: "Chứng từ hoàn thành" }];
  if (pathname.startsWith("/nv/hoan-thanh/")) {
    return [
      { label: "Chứng từ hoàn thành", to: "/nv/hoan-thanh" },
      { label: pathname.endsWith("/moi") ? "Tạo chứng từ" : "Chi tiết chứng từ" },
    ];
  }
  if (pathname === "/nv/phieu-xuat") return [{ label: "Tra cứu phiếu xuất" }];
  if (pathname.startsWith("/nv/phieu-xuat/")) {
    return [
      { label: "Tra cứu phiếu xuất", to: "/nv/phieu-xuat" },
      { label: "Chi tiết phiếu xuất" },
    ];
  }
  if (pathname === "/nv/ton-kho") return [{ label: "Tra cứu tồn kho" }];
  if (pathname.startsWith("/nv/ton-kho/")) {
    return [
      { label: "Tra cứu tồn kho", to: "/nv/ton-kho" },
      { label: "Chi tiết tồn kho" },
    ];
  }
  if (pathname === "/nv/phieu") return [{ label: "Phiếu của tôi" }];
  if (pathname.startsWith("/nv/xuat-nvl")) return [{ label: "Phiếu xuất NVL" }];
  if (pathname.startsWith("/nv/xuat-tp")) return [{ label: "Phiếu xuất TP" }];
  if (pathname === "/ho-so") return [{ label: "Hồ sơ & đổi mật khẩu" }];
  return [{ label: "Tổng quan" }];
}

export function MainLayout() {
  const { user, logout } = useAuth();
  const { confirm } = useFeedback();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isAdmin = user.ma_vai_tro === "quan_tri_vien";
  const isEmployee = user.ma_vai_tro === "nhan_vien";
  const groups = navigationFor(user.ma_vai_tro);
  const name = user.ho_ten || user.ten_dang_nhap;
  const avatarText = initials(name);

  useEffect(() => {
    if (isAdmin) {
      document.documentElement.dataset.adminTheme = "true";
    } else {
      delete document.documentElement.dataset.adminTheme;
    }
    if (isEmployee) {
      document.documentElement.dataset.employeeTheme = "true";
    } else {
      delete document.documentElement.dataset.employeeTheme;
    }
    return () => {
      delete document.documentElement.dataset.adminTheme;
      delete document.documentElement.dataset.employeeTheme;
    };
  }, [isAdmin, isEmployee]);

  function signOut() {
    confirm({
      title: "Đăng xuất",
      description: "Bạn có muốn kết thúc phiên làm việc?",
      hideImpact: true,
      variant: "logout",
      onConfirm: () => {
        logout();
        navigate("/dang-nhap", { replace: true });
      },
    });
  }

  const userMenu = (
    <details className="user-menu">
      <summary aria-label={`Tài khoản: ${name}`}>
        <span className="avatar" aria-hidden="true">{avatarText}</span>
        <span>
          <strong>{name}</strong>
          <small>
            {isAdmin
              ? "Quản trị viên hệ thống"
              : isEmployee && user.ma_nhan_vien
                ? `Nhân viên · ${user.ma_nhan_vien}`
                : ROLE_LABELS[user.ma_vai_tro]}
          </small>
        </span>
        <ChevronDown size={18} aria-hidden="true" />
      </summary>
      <div className="user-dropdown">
        <NavLink to="/ho-so">
          <UserRound size={16} aria-hidden="true" /> Hồ sơ & đổi mật khẩu
        </NavLink>
        <button type="button" onClick={signOut}>
          <LogOut size={16} aria-hidden="true" /> Đăng xuất
        </button>
      </div>
    </details>
  );

  if (isAdmin || isEmployee) {
    const crumbs = isAdmin ? adminBreadcrumbs(pathname) : employeeBreadcrumbs(pathname);
    return (
      <div className={`app-shell admin-shell ${isEmployee ? "employee-shell" : ""}`}>
        <a className="skip-link" href="#main-content">
          Đến nội dung chính
        </a>
        <div className="shell-body admin-shell-body">
          <Sidebar
            groups={groups}
            mobileOpen={menuOpen}
            onNavigate={() => setMenuOpen(false)}
            onSignOut={signOut}
            adminTheme={isAdmin}
            employeeTheme={isEmployee}
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
                  {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
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
              <div className="admin-topbar-right">
                {isEmployee && <span className="module-pill">Kho &amp; sản xuất</span>}
                {userMenu}
              </div>
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
    <div className="app-shell">
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
            {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
          </button>
          <div className="brand">
            XBIKE
            <small>Hệ thống quản lý kho & sản xuất</small>
          </div>
        </div>
        {userMenu}
      </header>
      <div className="shell-body">
        <Sidebar
          groups={groups}
          mobileOpen={menuOpen}
          onNavigate={() => setMenuOpen(false)}
          onSignOut={signOut}
        />
        <main id="main-content" className="page-body" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
