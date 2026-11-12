import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  ArrowLeftRight,
  BarChart3,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  Factory,
  FileCheck,
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
import employeeArtworkSource from "../assets/images/brand/employee-bicycle.png";
import { API } from "../lib/api/endpoints.js";
import { useResource } from "../lib/api/useResources.js";
import { canAccessPath } from "../features/auth/permissions.js";
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
  nv: Home,
};

function SidebarLink({ path, label, onNavigate, darkTheme, badge }) {
  const segment = path.split("/").at(-1);
  const Icon =
    path === "/nv" || (segment === "admin" && darkTheme)
      ? Home
      : path === "/nv/yeu-cau"
        ? ClipboardList
        : path === "/nv/lenh-sx"
          ? Factory
          : path === "/nv/hoan-thanh"
            ? FileCheck
            : path === "/nv/phieu-xuat"
              ? Package
              : path === "/nv/ton-kho"
                ? Boxes
                : sectionIcons[segment] || LayoutDashboard;
  return (
    <NavLink
      to={path}
      end={path === "/admin" || path === "/kho" || path === "/nv"}
      aria-label={label}
      title={label}
      onClick={onNavigate}
      className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ""}`}
    >
      <Icon size={darkTheme ? 22 : 19} strokeWidth={1.85} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
      {badge !== undefined && <span className={styles.badge} aria-hidden="true">{badge}</span>}
    </NavLink>
  );
}

export function Sidebar({
  groups,
  mobileOpen,
  onNavigate,
  onSignOut,
  adminTheme = false,
  employeeTheme = false,
}) {
  const { pathname } = useLocation();
  const darkTheme = adminTheme || employeeTheme;
  const assignedRequests = useResource(
    API.requests,
    { page: 1, page_size: 1 },
    employeeTheme && canAccessPath("nhan_vien", pathname),
  );
  const [collapsed, setCollapsed] = useState(false);
  const toggleLabel = collapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng";
  return (
    <aside
      id="main-navigation"
      aria-label="Thanh điều hướng"
      className={`${styles.root} ${darkTheme ? styles.admin : ""} ${employeeTheme ? styles.employee : ""} ${collapsed && !darkTheme ? styles.collapsed : ""} ${mobileOpen ? styles.open : ""}`}
    >
      {darkTheme ? (
        <div className={styles.adminBrand}>
          {employeeTheme ? (
            <div className={styles.employeeBrand}>
              <div className={styles.brandLogo} aria-label="XBIKE MRP SYSTEM">
                XBIKE
              </div>
              <div className={styles.brandSubline}>
                MRP SYSTEM<span className={styles.brandTrademark}>™</span>
              </div>
            </div>
          ) : (
            <img src={logo} alt="XBIKE MRP System" className={styles.adminLogo} />
          )}
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
            {!darkTheme && <div className={styles.groupTitle}>{group.title}</div>}
            {group.items.map(([path, label]) => (
              <SidebarLink
                key={path}
                path={path}
                label={label}
                onNavigate={onNavigate}
                darkTheme={darkTheme}
                badge={employeeTheme && path === "/nv/yeu-cau" ? assignedRequests.data?.meta.total : undefined}
              />
            ))}
          </div>
        ))}
        {!adminTheme && (
          <div className={styles.account}>
            <SidebarLink
              path="/ho-so"
              label="Hồ sơ & đổi mật khẩu"
              onNavigate={onNavigate}
              darkTheme={darkTheme}
            />
            <button
              type="button"
              className={styles.link}
              aria-label="Đăng xuất"
              title="Đăng xuất"
              onClick={onSignOut}
            >
              <LogOut size={darkTheme ? 22 : 19} strokeWidth={1.75} aria-hidden="true" />
              <span className={styles.label}>Đăng xuất</span>
            </button>
          </div>
        )}
      </nav>
      {darkTheme && (
        <div className={styles.adminArtwork} aria-hidden="true">
          <img src={employeeTheme ? employeeArtworkSource : adminArtworkSource} alt="" />
        </div>
      )}
    </aside>
  );
}
