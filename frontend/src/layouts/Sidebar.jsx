import { NavLink, useLocation } from "react-router-dom";
import {
  ArrowLeftRight,
  BadgeCheck,
  BarChart3,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  Factory,
  FileCheck,
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
import adminArtworkSource from "../assets/images/admin/sidebar-artwork.webp";
import employeeArtworkSource from "../assets/images/brand/employee-bicycle.png";
import artworkSource from "../assets/images/login/slide-02-touring.webp";
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
  "chung-tu-hoan-thanh": FileCheck,
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

const employeeIcons = {
  "/nv": Home,
  "/nv/yeu-cau": ClipboardList,
  "/nv/lenh-sx": Factory,
  "/nv/hoan-thanh": FileCheck,
  "/nv/chung-tu-hoan-thanh": FileCheck,
  "/nv/phieu-xuat": Package,
  "/nv/ton-kho": Boxes,
};

function SidebarLink({ path, label, onNavigate, adminTheme, warehouseTheme, employeeTheme, badge }) {
  const segment = path.split("/").at(-1);
  const Icon =
    (warehouseTheme && warehouseIcons[segment]) ||
    employeeIcons[path] ||
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
      <Icon size={adminTheme || employeeTheme ? 22 : 19} strokeWidth={1.85} aria-hidden="true" />
      <span className={styles.label}>{label}</span>
      {badge !== undefined && <span className={styles.badge} aria-hidden="true">{badge}</span>}
    </NavLink>
  );
}

export function Sidebar({
  groups,
  mobileOpen,
  onNavigate,
  adminTheme = false,
  warehouseTheme = false,
  employeeTheme = false,
}) {
  const { pathname } = useLocation();
  const darkTheme = adminTheme || employeeTheme;
  const assignedRequests = useResource(
    API.requests,
    { page: 1, page_size: 1 },
    employeeTheme && canAccessPath("nhan_vien", pathname),
  );
  const completedRequests = useResource(
    API.requests,
    { page: 1, page_size: 1, trang_thai: "hoan_thanh" },
    employeeTheme && canAccessPath("nhan_vien", pathname),
  );
  const cancelledRequests = useResource(
    API.requests,
    { page: 1, page_size: 1, trang_thai: "da_huy" },
    employeeTheme && canAccessPath("nhan_vien", pathname),
  );
  const totalAssigned = assignedRequests.data?.meta?.total;
  const completedAssigned = completedRequests.data?.meta?.total;
  const cancelledAssigned = cancelledRequests.data?.meta?.total;
  const isAssignedPending = assignedRequests.isPending || assignedRequests.isLoading;
  const isCompletedPending = completedRequests.isPending || completedRequests.isLoading;
  const isCancelledPending = cancelledRequests.isPending || cancelledRequests.isLoading;
  const isAssignedError = Boolean(assignedRequests.isError || assignedRequests.error);
  const isCompletedError = Boolean(completedRequests.isError || completedRequests.error);
  const isCancelledError = Boolean(cancelledRequests.isError || cancelledRequests.error);

  const hasValidBadgeCounts =
    !isAssignedPending &&
    !isCompletedPending &&
    !isCancelledPending &&
    !isAssignedError &&
    !isCompletedError &&
    !isCancelledError &&
    typeof totalAssigned === "number" &&
    typeof completedAssigned === "number" &&
    typeof cancelledAssigned === "number";

  const activeAssignedCount = hasValidBadgeCounts
    ? Math.max(0, totalAssigned - completedAssigned - cancelledAssigned)
    : undefined;
  return (
    <aside
      id="main-navigation"
      aria-label="Thanh điều hướng"
      className={`${styles.root} ${darkTheme ? styles.admin : ""} ${employeeTheme ? styles.employee : ""} ${mobileOpen ? styles.open : ""}`}
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
            <img src={logo} alt="XBIKE MRP System" className={styles.logo} />
          )}
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
            {!darkTheme && <div className={styles.groupTitle}>{group.title}</div>}
            {group.items.map(([path, label]) => (
              <SidebarLink
                key={path}
                path={path}
                label={label}
                onNavigate={onNavigate}
                adminTheme={adminTheme}
                warehouseTheme={warehouseTheme}
                employeeTheme={employeeTheme}
                badge={employeeTheme && path === "/nv/yeu-cau" ? activeAssignedCount : undefined}
              />
            ))}
          </div>
        ))}
        {!darkTheme && (
          <div className={styles.artwork} aria-hidden="true">
            <img src={artworkSource} alt="" />
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
