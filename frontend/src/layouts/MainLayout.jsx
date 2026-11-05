import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, Menu, UserRound, X } from "lucide-react";
import { useAuth } from "../features/auth/AuthProvider.jsx";
import { useFeedback } from "../components/FeedbackProvider.jsx";
import { ROLE_LABELS } from "../lib/format.js";
import { navigationFor } from "./navigation.js";
import { Sidebar } from "./Sidebar.jsx";
export function MainLayout() {
  const { user, logout } = useAuth();
  const { confirm } = useFeedback();
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const groups = navigationFor(user.ma_vai_tro);
  const name = user.ho_ten || user.ten_dang_nhap;
  function signOut() {
    confirm({
      title: "Đăng xuất",
      description: "Bạn muốn kết thúc phiên làm việc? Hãy lưu các thay đổi trước khi đăng xuất.",
      onConfirm: () => {
        logout();
        navigate("/dang-nhap", { replace: true });
      },
    });
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
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
          <div className="brand">
            XBIKE
            <small>
              {user.ma_vai_tro === "quan_tri_vien"
                ? "Giao diện quản trị"
                : "Hệ thống quản lý kho & sản xuất"}
            </small>
          </div>
        </div>
        <details className="user-menu">
          <summary>
            <span className="avatar">
              {name
                .split(/\s+/)
                .slice(-2)
                .map((part) => part[0])
                .join("")
                .toUpperCase()}
            </span>
            <span>
              <strong>{name}</strong>
              <small>{ROLE_LABELS[user.ma_vai_tro]}</small>
            </span>
            <ChevronDown size={18} />
          </summary>
          <div className="user-dropdown">
            <NavLink to="/ho-so">
              <UserRound size={16} /> Hồ sơ & đổi mật khẩu
            </NavLink>
            <button type="button" onClick={signOut}>
              <LogOut size={16} /> Đăng xuất
            </button>
          </div>
        </details>
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
