import React from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import {
  Bike,
  Boxes,
  ClipboardList,
  Compass,
  FileCheck2,
  HardHat,
  LayoutDashboard,
  Layers,
  PackageCheck,
  Send,
  ShieldCheck,
  Truck,
  Users,
} from "lucide-react";

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  badge?: string;
}

export const MainLayout: React.FC = () => {
  const location = useLocation();

  const navigation: { section: string; items: NavItem[] }[] = [
    {
      section: "Overview",
      items: [
        { name: "Dashboard", path: "/", icon: <LayoutDashboard size={18} /> },
        { name: "MRP Run & Reports", path: "/reports", icon: <Compass size={18} /> },
      ],
    },
    {
      section: "Engineering & Procurement",
      items: [
        { name: "Materials Catalog", path: "/materials", icon: <Boxes size={18} /> },
        { name: "Bicycle Products", path: "/products", icon: <Bike size={18} /> },
        { name: "Bill of Materials (BOM)", path: "/bom", icon: <Layers size={18} /> },
        { name: "Suppliers & Vendors", path: "/suppliers", icon: <Truck size={18} /> },
      ],
    },
    {
      section: "Shop Floor & Warehouse",
      items: [
        { name: "Inventory & Stock", path: "/inventory", icon: <PackageCheck size={18} /> },
        { name: "Receiving & QA", path: "/receiving", icon: <FileCheck2 size={18} /> },
        { name: "Material Issuing", path: "/material-issuing", icon: <ClipboardList size={18} /> },
        { name: "Production Orders", path: "/production", icon: <HardHat size={18} />, badge: "8 Active" },
        { name: "Finished Goods Dispatch", path: "/finished-goods-issuing", icon: <Send size={18} /> },
      ],
    },
    {
      section: "Administration",
      items: [
        { name: "Audit Trail", path: "/audit", icon: <ShieldCheck size={18} /> },
        { name: "User Roles", path: "/users", icon: <Users size={18} /> },
      ],
    },
  ];

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <Bike size={22} />
          </div>
          <div>
            <h1 className="brand-title">xBike MRP</h1>
            <span style={{ fontSize: "0.68rem", color: "var(--accent-cyan)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
              Manufacturing ERP
            </span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navigation.map((group) => (
            <div key={group.section}>
              <div className="nav-section-title">{group.section}</div>
              {group.items.map((item) => {
                const isActive =
                  item.path === "/"
                    ? location.pathname === "/"
                    : location.pathname.startsWith(item.path);

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-link ${isActive ? "active" : ""}`}
                  >
                    {item.icon}
                    <span style={{ flex: 1 }}>{item.name}</span>
                    {item.badge && (
                      <span className="badge badge-cyan" style={{ fontSize: "0.65rem", padding: "1px 6px" }}>
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="main-content">
        <header className="top-header">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="badge badge-emerald">Plant #1 • Online</span>
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              Shift: Morning A (06:00 - 14:00)
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #06b6d4, #3b82f6)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                SA
              </div>
              <div style={{ fontSize: "0.85rem" }}>
                <div style={{ fontWeight: 600 }}>System Admin</div>
                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>admin@xbike.local</div>
              </div>
            </div>
          </div>
        </header>

        <main className="page-body">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
