import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  CircleCheck,
  Factory,
  FilePlus2,
  HelpCircle,
  Menu,
  Moon,
  RotateCcw,
  Sun,
  X,
} from "lucide-react";
import { createDemoApi } from "./demo-api";
import { ActionButton, ConfirmDialog, Status } from "./components";
import type { WorkspaceContext } from "./workspace-hooks";
import { currentManager } from "./types";
import "./management.css";

const navigation = [
  {
    path: "nhap-kho",
    label: "Phiếu nhập kho",
    icon: ArrowDownToLine,
    description: "Tiếp nhận vật tư",
  },
  {
    path: "yeu-cau-thanh-pham",
    label: "Yêu cầu thành phẩm",
    icon: FilePlus2,
    description: "Tính nhu cầu sản xuất",
  },
  {
    path: "lenh-san-xuat",
    label: "Lệnh sản xuất",
    icon: Factory,
    description: "Giao và gửi lệnh",
  },
  {
    path: "duyet-phieu-xuat",
    label: "Duyệt phiếu xuất",
    icon: CircleCheck,
    description: "Kiểm tra và cấp vật tư",
  },
];

export function ManagerLayout() {
  const [api] = useState(createDemoApi);
  const [queryKey] = useState(() => ["management-demo", crypto.randomUUID()]);
  const [theme, setTheme] = useState(() =>
    localStorage.getItem("xbike-ui-theme") === "dark" ? "dark" : "light",
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [revision, setRevision] = useState(0);
  const [toast, setToast] = useState<{ title: string; description?: string } | null>(null);
  const queryClient = useQueryClient();
  const workspace = useQuery({
    queryKey,
    queryFn: api.workspace,
    staleTime: Infinity,
    retry: false,
  });
  const location = useLocation();
  const current =
    navigation.find((entry) => location.pathname.includes(entry.path)) ?? navigation[0];
  const pending =
    workspace.data?.issues.filter((entry) => entry.status === "cho_duyet").length ?? 0;
  useEffect(() => {
    localStorage.setItem("xbike-ui-theme", theme);
    document.documentElement.style.colorScheme = theme;
    return () => {
      document.documentElement.style.colorScheme = "";
    };
  }, [theme]);
  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 5500);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    if (!menuOpen || !sidebar.current) return;
    const previous = document.activeElement;
    const panel = sidebar.current;
    const controls = () =>
      Array.from(panel.querySelectorAll<HTMLElement>("a[href], button:not(:disabled)"));
    controls()[0]?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
      if (event.key !== "Tab") return;
      const elements = controls();
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    panel.addEventListener("keydown", onKeyDown);
    return () => {
      panel.removeEventListener("keydown", onKeyDown);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [menuOpen]);

  async function reset() {
    setResetting(true);
    try {
      const updated = await api.reset();
      queryClient.setQueryData(queryKey, updated);
      setRevision((value) => value + 1);
      setResetOpen(false);
      setToast({
        title: "Đã đặt lại dữ liệu demo",
        description: "Tồn kho và chứng từ trở về trạng thái ban đầu.",
      });
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="manager-workspace" data-theme={theme}>
      <a className="m-skip" href="#manager-content">
        Đến nội dung chính
      </a>
      {menuOpen && (
        <button
          className="m-nav-backdrop"
          aria-label="Đóng điều hướng"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside
        ref={sidebar}
        className={`m-sidebar ${menuOpen ? "m-sidebar--open" : ""}`}
        role={menuOpen ? "dialog" : undefined}
        aria-modal={menuOpen ? true : undefined}
        aria-label="Điều hướng quản lý"
      >
        <ActionButton
          variant="plain"
          className="m-nav-close"
          aria-label="Đóng menu"
          onClick={() => setMenuOpen(false)}
        >
          <X size={18} />
        </ActionButton>
        <Link
          className="m-brand"
          to="/quan-ly/nhap-kho"
          onClick={() => setMenuOpen(false)}
          aria-label="xBike MRP — Không gian quản lý"
        >
          <svg viewBox="0 0 40 34" width="39" height="34" fill="none" aria-hidden="true">
            <circle cx="9" cy="24" r="7" />
            <circle cx="31" cy="24" r="7" />
            <path d="M9 24 17 10l7 14H9l14-15 8 15M14 10h7M25 5h6" />
          </svg>
          <span>
            <strong>
              xBike<span> MRP</span>
            </strong>
            <small>Manufacturing workspace</small>
          </span>
        </Link>
        <div className="m-workspace-switch">
          <span className="m-workspace-monogram">XB</span>
          <div>
            <strong>Xưởng sản xuất xBike</strong>
            <small>Không gian quản lý</small>
          </div>
        </div>
        <div className="m-nav-label">Điều phối sản xuất</div>
        <nav aria-label="Bốn nghiệp vụ quản lý">
          {navigation.map(({ path, label, icon: Icon, description }) => (
            <NavLink
              key={path}
              to={`/quan-ly/${path}`}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) => `m-nav-link ${isActive ? "is-active" : ""}`}
            >
              <Icon size={18} strokeWidth={1.65} aria-hidden="true" />
              <span>
                {label}
                <small>{description}</small>
              </span>
              {path === "duyet-phieu-xuat" && pending > 0 && (
                <span className="m-nav-count" aria-label={`${pending} phiếu chờ duyệt`}>
                  {pending}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="m-sidebar-note">
          <div className="m-loop-mark">
            <Factory size={20} />
            <ArrowRight size={15} />
            <CircleCheck size={20} />
          </div>
          <strong>Từ vật tư đến thành phẩm</strong>
          <p>Mỗi chứng từ là một bước trong luồng sản xuất.</p>
        </div>
        <div className="m-sidebar-bottom">
          <button
            className="m-help-button"
            onClick={() => {
              setHelpOpen(true);
              setMenuOpen(false);
            }}
          >
            <HelpCircle size={17} />
            Hướng dẫn bản demo
          </button>
          <div className="m-account">
            <span className="m-avatar">TB</span>
            <div>
              <strong>{currentManager.name}</strong>
              <small>Quản lý · Tài khoản minh họa</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="m-workspace-body">
        <header className="m-topbar">
          <div className="m-breadcrumb">
            <ActionButton
              className="m-mobile-menu"
              variant="plain"
              aria-label="Mở điều hướng"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((value) => !value)}
            >
              <Menu size={21} />
            </ActionButton>
            <span>Quản lý</span>
            <span className="m-breadcrumb-slash">/</span>
            <strong>{current.label}</strong>
          </div>
          <div className="m-topbar-actions">
            <Status>Demo v3.1</Status>
            <span className="m-topbar-divider" />
            <ActionButton
              variant="plain"
              aria-label={
                theme === "light" ? "Chuyển sang giao diện tối" : "Chuyển sang giao diện sáng"
              }
              title="Đổi giao diện"
              onClick={() => setTheme((value) => (value === "light" ? "dark" : "light"))}
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </ActionButton>
            <ActionButton
              variant="plain"
              aria-label="Đặt lại dữ liệu demo"
              title="Đặt lại demo"
              onClick={() => setResetOpen(true)}
            >
              <RotateCcw size={17} />
            </ActionButton>
          </div>
        </header>
        <main id="manager-content" className="m-content">
          {workspace.isPending ? (
            <div className="m-loading" role="status">
              <span className="m-skeleton m-skeleton-title" />
              <span className="m-skeleton" />
              <span className="m-skeleton m-skeleton-panel" />
              <p>Đang chuẩn bị không gian quản lý…</p>
            </div>
          ) : workspace.isError ? (
            <section className="m-load-error" role="alert">
              <h1>Chưa tải được dữ liệu</h1>
              <p>{workspace.error.message}</p>
              <ActionButton onClick={() => void workspace.refetch()}>Thử lại</ActionButton>
            </section>
          ) : (
            <Outlet
              key={revision}
              context={
                {
                  workspace: workspace.data,
                  api,
                  queryKey,
                  notify: (title, description) => setToast({ title, description }),
                } satisfies WorkspaceContext
              }
            />
          )}
          <footer className="m-page-footer">
            <span>
              xBike MRP <span>·</span> Không gian điều phối sản xuất
            </span>
            <span>Dữ liệu minh họa · Làm mới trang để bắt đầu lại</span>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="m-toast" role="status">
          <span className="m-toast-icon">
            <Check size={18} />
          </span>
          <div>
            <strong>{toast.title}</strong>
            {toast.description && <p>{toast.description}</p>}
          </div>
          <ActionButton variant="plain" aria-label="Đóng thông báo" onClick={() => setToast(null)}>
            <X size={16} />
          </ActionButton>
        </div>
      )}
      {resetOpen && (
        <ConfirmDialog
          title="Đặt lại dữ liệu demo?"
          confirmLabel="Đặt lại dữ liệu"
          onClose={() => setResetOpen(false)}
          onConfirm={() => void reset()}
          busy={resetting}
        >
          <p>
            Các phiếu vừa tạo và thay đổi tồn kho trong bản demo sẽ được đặt lại. Thao tác này không
            liên quan đến database backend.
          </p>
        </ConfirmDialog>
      )}
      {helpOpen && (
        <ConfirmDialog
          title="Bốn bước điều phối sản xuất"
          confirmLabel="Bắt đầu thao tác"
          onClose={() => setHelpOpen(false)}
          onConfirm={() => setHelpOpen(false)}
        >
          <ol className="m-help-list">
            <li>Lưu nháp phiếu nhập; xác nhận để tăng tồn.</li>
            <li>Lưu nháp yêu cầu, tính kế hoạch rồi gửi để sinh cây lệnh.</li>
            <li>Chọn lệnh đã sinh, giao nhân viên và gửi lệnh.</li>
            <li>Kiểm tra tồn rồi duyệt hoặc từ chối phiếu xuất.</li>
          </ol>
          <p className="m-muted">
            Dữ liệu được mô phỏng trong tab này, không gửi đến backend. Có sẵn một phiếu thiếu tồn
            để anh thử luồng từ chối.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}
