import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, Menu, UserRound, X } from "lucide-react";
import { useAuth } from "../features/auth/AuthProvider.jsx";
import { useFeedback } from "../components/FeedbackProvider.jsx";
import { ROLE_LABELS, today } from "../lib/format.js";
import { navigation } from "./navigation.js";
export function MainLayout() {
  const { user, logout } = useAuth();
  const { confirm } = useFeedback();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const groups = navigation[user.ma_vai_tro] || [];
  const current =
    groups.flatMap((group) => group.items).find(([path]) => location.pathname === path) ||
    groups
      .flatMap((group) => group.items)
      .filter(([path]) => location.pathname.startsWith(`${path}/`))
      .sort((left, right) => right[0].length - left[0].length)[0];
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
          <div className="breadcrumb">
            {current?.[1] || "Hồ sơ"}
            <span> / {ROLE_LABELS[user.ma_vai_tro]}</span>
          </div>
          <time className="header-date">{today().split("-").reverse().join("/")}</time>
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
        <aside id="main-navigation" className={`sidebar ${menuOpen ? "is-open" : ""}`}>
          <nav aria-label="Điều hướng nghiệp vụ">
            {groups.map((group) => (
              <div className="nav-group" key={group.title}>
                <div className="nav-group-title">{group.title}</div>
                {group.items.map(([path, label]) => (
                  <NavLink
                    key={path}
                    to={path}
                    end={path === "/admin" || path === "/kho" || path === "/nv"}
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                  >
                    {label}
                  </NavLink>
                ))}
              </div>
            ))}
            <div className="nav-account">
              <NavLink to="/ho-so" className="nav-link" onClick={() => setMenuOpen(false)}>
                Hồ sơ & đổi mật khẩu
              </NavLink>
              <button type="button" className="nav-link" onClick={signOut}>
                Đăng xuất
              </button>
            </div>
          </nav>
          <div className="sidebar-footer">
            XBIKE MRP<small>Một hệ thống · Ba vai trò</small>
          </div>
        </aside>
        <main id="main-content" className="page-body" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
