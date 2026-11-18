import { NavLink } from "react-router-dom";
import {
  ArrowLeftRight,
  BadgeCheck,
  BarChart3,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  Factory,
  GitBranch,
  History,
  Home,
  Layers,
  LayoutDashboard,
  Network,
  Package,
  PackageMinus,
  PackagePlus,
  SlidersHorizontal,
  Ticket,
  Truck,
  TrendingUp,
  Users,
} from "lucide-react";
import logo from "../assets/images/brand/xbike-logo.svg";
import artworkSource from "../assets/images/login/slide-02-touring.webp";
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
};

const warehouseIcons = {
  kho: LayoutDashboard,
  "mat-hang": Boxes,
  "nha-cung-cap": Truck,
  bom: GitBranch,
  "phieu-nhap": PackagePlus,
  "nhu-cau-bo-sung": ClipboardList,
  "yeu-cau": ClipboardList,
  "phieu-xuat": PackageMinus,
  "chung-tu-hoan-thanh": BadgeCheck,
  "thong-ke": TrendingUp,
  "giao-dich": History,
  "lich-su": History,
};

function SidebarLink({ path, label, onNavigate, adminTheme, warehouseTheme }) {
  const segment = path.split("/").at(-1);
  const Icon =
    (warehouseTheme && warehouseIcons[segment]) ||
    (segment === "admin" && adminTheme ? Home : sectionIcons[segment]) ||
    LayoutDashboard;
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

export function Sidebar({
  groups,
  mobileOpen,
  onNavigate,
  adminTheme = false,
  warehouseTheme = false,
}) {
  return (
    <aside
      id="main-navigation"
      aria-label="Thanh điều hướng"
      className={`${styles.root} ${adminTheme ? styles.admin : ""} ${mobileOpen ? styles.open : ""}`}
    >
      {adminTheme ? (
        <div className={styles.adminBrand}>
          <img src={logo} alt="XBIKE MRP System" className={styles.logo} />
        </div>
      ) : (
        <div className={styles.toolbar}>
          <img src={logo} alt="XBIKE MRP System" className={styles.logo} />
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
                warehouseTheme={warehouseTheme}
              />
            ))}
          </div>
        ))}
        <div className={styles.artwork} aria-hidden="true">
          <img src={artworkSource} alt="" />
        </div>
      </nav>
    </aside>
  );
}
