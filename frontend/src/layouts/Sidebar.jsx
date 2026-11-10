import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  ArrowLeftRight,
  BarChart3,
  ClipboardCheck,
  ClipboardList,
  Factory,
  History,
  Home,
  Layers,
  LayoutDashboard,
  LogOut,
  Network,
  Package,
  PackageMinus,
  PanelLeftClose,
  PanelLeftOpen,
  SlidersHorizontal,
  Ticket,
  Truck,
  UserRound,
  Users,
} from "lucide-react";
import logo from "../assets/images/brand/xbike-logo.svg";
import adminArtworkSource from "../../../doc/ui-spec-admin/tong_quan.png";
import styles from "./Sidebar.module.css";

const sectionIcons = {
  admin: Home,
  "tai-khoan": Users,
  "vai-tro": Layers,
  "lich-su": History,
  "mat-hang": Package,
  "ton-kho": Package,
  "nha-cung-cap": Truck,
  "phieu-nhap": ClipboardList,
  "giao-dich": ArrowLeftRight,
  bom: Network,
  "yeu-cau": ClipboardCheck,
  "lenh-sx": Factory,
  "phieu-xuat": PackageMinus,
  "duyet-hoan-thanh": ClipboardCheck,
  "hoan-thanh": ClipboardCheck,
  "dieu-chinh": SlidersHorizontal,
  ticket: Ticket,
  "thong-ke": BarChart3,
  "ho-so": UserRound,
};

function SidebarLink({ path, label, onNavigate, adminTheme }) {
  const segment = path.split("/").at(-1);
  const Icon =
    segment === "admin" && adminTheme ? Home : sectionIcons[segment] || LayoutDashboard;
  return (
    <NavLink
      to={path}
      end={path === "/admin" || path === "/kho" || path === "/nv"}
      aria-label={label}
      title={label}
      onClick={onNavigate}
      className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
    >
      <Icon size={adminTheme ? 22 : 19} strokeWidth={1.85} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
    </NavLink>
  );
}

export function Sidebar({ groups, mobileOpen, onNavigate, onSignOut, adminTheme = false }) {
  const [collapsed, setCollapsed] = useState(false);
  const toggleLabel = collapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng";
  return (
    <aside
      id="main-navigation"
      aria-label="Thanh điều hướng"
      className={`${styles.root} ${adminTheme ? styles.admin : ""} ${collapsed && !adminTheme ? styles.collapsed : ""} ${mobileOpen ? styles.open : ""}`}
    >
      {adminTheme ? (
        <div className={styles.adminBrand}>
          <img src={logo} alt="XBIKE MRP System" className={styles.adminLogo} />
        </div>
      ) : (
        <div className={styles.toolbar}>
          <button
            type="button"
            className={styles.toggle}
            aria-label={toggleLabel}
            title={toggleLabel}
            aria-expanded={!collapsed}
            aria-controls="sidebar-navigation-items"
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <PanelLeftOpen size={19} strokeWidth={1.75} aria-hidden="true" />
            ) : (
              <PanelLeftClose size={19} strokeWidth={1.75} aria-hidden="true" />
            )}
          </button>
        </div>
      )}
      <nav
        id="sidebar-navigation-items"
        className={styles.navigation}
        aria-label="Điều hướng nghiệp vụ"
      >
        {groups.map((group) => (
          <div className={styles.group} key={group.title}>
            {!adminTheme && <div className={styles.groupTitle}>{group.title}</div>}
            {group.items.map(([path, label]) => (
              <SidebarLink
                key={path}
                path={path}
                label={label}
                onNavigate={onNavigate}
                adminTheme={adminTheme}
              />
            ))}
          </div>
        ))}
        {!adminTheme && (
          <div className={styles.account}>
            <SidebarLink path="/ho-so" label="Hồ sơ & đổi mật khẩu" onNavigate={onNavigate} />
            <button
              type="button"
              className={styles.link}
              aria-label="Đăng xuất"
              title="Đăng xuất"
              onClick={onSignOut}
            >
              <LogOut size={19} strokeWidth={1.75} aria-hidden="true" />
              <span className={styles.label}>Đăng xuất</span>
            </button>
          </div>
        )}
      </nav>
      {adminTheme && (
        <div className={styles.adminArtwork} aria-hidden="true">
          <img src={adminArtworkSource} alt="" />
        </div>
      )}
    </aside>
  );
}
