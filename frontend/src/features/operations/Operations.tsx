import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation, useSearchParams } from "react-router-dom";
import {
  Bike,
  Box,
  ClipboardList,
  Factory,
  Menu,
  RefreshCw,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Button } from "@/components/Button";
import {
  date,
  fmt,
  label,
  localDay,
  stock,
  type Adjustment,
  type Item,
  type Ledger,
  type Order,
  type Page,
  type Role,
} from "./model";
import { DemoProvider, Field, Modal, Notice, Status, Table, useDemo } from "./shared";
import { Detail } from "./Detail";
import "./operations.css";

const pages: Record<Page, { title: string; description: string; icon: ReactNode }> = {
  mathang: {
    title: "Mặt hàng và tồn kho",
    description: "Tra cứu danh mục, giá và số lượng tồn hiện tại.",
    icon: <Box size={19} />,
  },
  lenhsanxuat: {
    title: "Lệnh sản xuất",
    description: "Theo dõi giao việc, cấp vật tư và tiến độ sản xuất.",
    icon: <Factory size={19} />,
  },
  giaodichkho: {
    title: "Giao dịch kho",
    description: "Theo dõi từng biến động và truy vết chứng từ đã ghi sổ.",
    icon: <ClipboardList size={19} />,
  },
  dieuchinhkho: {
    title: "Điều chỉnh kho",
    description: "Đối chiếu số lượng trên phiếu nhập đã hoàn thành.",
    icon: <SlidersHorizontal size={19} />,
  },
};
export function OperationsLayout() {
  return (
    <DemoProvider>
      <Shell />
    </DemoProvider>
  );
}
function Shell() {
  const { role, setRole, warning, notice, reset } = useDemo();
  const [menu, setMenu] = useState(false);
  const [resetting, setResetting] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const location = useLocation();
  useEffect(() => {
    setMenu(false);
  }, [location.pathname]);
  useEffect(() => {
    if (!menu) return;
    const closeMenu = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenu(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener("keydown", closeMenu);
    return () => document.removeEventListener("keydown", closeMenu);
  }, [menu]);
  return (
    <div className="op-root" lang="vi">
      <a className="op-skip" href="#op-main">
        Đến nội dung chính
      </a>
      <header className="op-topbar">
        <button
          className="op-menu op-icon"
          ref={menuButton}
          aria-label={menu ? "Đóng điều hướng" : "Mở điều hướng"}
          aria-controls="op-nav"
          aria-expanded={menu}
          onClick={() => setMenu(!menu)}
        >
          {menu ? <X /> : <Menu />}
        </button>
        <Link to="/mathang" className="op-brand">
          <Bike size={32} />
          <span>
            XBIKE<small>QUẢN LÝ KHO & SẢN XUẤT</small>
          </span>
        </Link>
        <span className="op-top-context">Bàn làm việc</span>
        <span className="op-demo-tag">Bản demo · Chưa kết nối API</span>
        <span className="op-profile">
          {role === "Q" ? "Nguyễn Văn An" : role === "N" ? "Trần Minh Tuấn" : "Quản trị viên"}
          <small>
            {role === "Q"
              ? "Quản lý kho"
              : role === "N"
                ? "Nhân viên sản xuất"
                : "Quản trị tài khoản"}
          </small>
        </span>
      </header>
      <aside id="op-nav" className={`op-sidebar ${menu ? "open" : ""}`}>
        <nav aria-label="Điều hướng nghiệp vụ">
          <p>Quản lý kho & sản xuất</p>
          {Object.entries(pages).map(([path, config]) => (
            <NavLink key={path} to={`/${path}`}>
              {config.icon}
              {config.title}
            </NavLink>
          ))}
        </nav>
        <div className="op-sidebar-foot">
          <Field label="Xem demo theo vai trò">
            <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
              <option value="Q">Quản lý kho</option>
              <option value="N">Nhân viên · Minh Tuấn</option>
              <option value="A">Quản trị viên</option>
            </select>
          </Field>
          <small>Dữ liệu minh họa lưu trong phiên trình duyệt.</small>
          <button className="op-text-button" onClick={() => setResetting(true)}>
            Khôi phục dữ liệu mẫu
          </button>
          <Link to="/">Về giao diện hiện có</Link>
        </div>
      </aside>
      <main className="op-main" id="op-main" tabIndex={-1}>
        {warning && <Notice tone="warning">{warning}</Notice>}
        <div className="op-feedback" role="status" aria-live="polite">
          {notice}
        </div>
        <Outlet />
      </main>
      {resetting && (
        <Modal
          title="Khôi phục dữ liệu mẫu?"
          onClose={() => setResetting(false)}
          submitLabel="Khôi phục"
          onSubmit={() => {
            reset();
            setResetting(false);
          }}
        >
          <Notice>
            Thao tác này xóa các thay đổi demo trong phiên hiện tại. Dữ liệu ứng dụng và database
            không bị tác động.
          </Notice>
        </Modal>
      )}
    </div>
  );
}
type Row = Item | Order | Ledger | Adjustment;
const code = (row: Row) =>
  "sku" in row
    ? row.ma_mat_hang
    : "ma_lenh_san_xuat" in row
      ? row.ma_lenh_san_xuat
      : "ma_phieu" in row
        ? row.ma_phieu
        : `GD-${row.id}`;
const stateOf = (row: Row) =>
  "sku" in row
    ? String(row.is_active)
    : "loai_giao_dich" in row
      ? row.loai_giao_dich
      : row.trang_thai;
export function OperationsPage({ page }: { page: Page }) {
  const { db, role } = useDemo();
  const [params, setParams] = useSearchParams();
  const config = pages[page];
  const get = (key: string) => params.get(key) || "";
  const set = (key: string, value: string) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(key, value);
        else next.delete(key);
        if (key !== "p" && key !== "id") next.delete("p");
        return next;
      },
      { replace: true },
    );
  const open = (id: string) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.set("id", id);
      return next;
    });
  const close = () =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("id");
        next.delete("source");
        return next;
      },
      { replace: true },
    );
  const clear = () => setParams({});
  useEffect(() => {
    document.title = `${config.title} · xBike`;
  }, [config.title]);
  const denied = role === "A" || (role === "N" && ["giaodichkho", "dieuchinhkho"].includes(page));
  const base: Row[] =
    page === "mathang"
      ? db.items
      : page === "giaodichkho"
        ? db.ledger
        : page === "dieuchinhkho"
          ? db.adjustments
          : db.orders.filter((x) => role !== "N" || x.nhan_vien_id === 21);
  const variants =
    page === "mathang"
      ? ["true", "false"]
      : page === "lenhsanxuat"
        ? ["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"]
        : page === "dieuchinhkho"
          ? ["nhap", "da_xac_nhan", "loi"]
          : [
              "nhap_vat_tu",
              "xuat_vat_tu",
              "nhap_san_pham_san_xuat",
              "xuat_thanh_pham",
              "dieu_chinh_ton_kho",
            ];
  const q = get("q").trim().toLocaleLowerCase("vi");
  const rows = base
    .filter((row) => {
      if (get("status") && stateOf(row) !== get("status")) return false;
      const item =
        "mat_hang_id" in row ? db.items.find((x) => x.id === row.mat_hang_id) : undefined;
      const searchable = `${code(row)} ${"sku" in row ? row.ten_mat_hang + " " + row.sku : "ly_do" in row ? row.ly_do : "source" in row ? row.source + " " + item?.ten_mat_hang : item?.ten_mat_hang}`;
      if (q && !searchable.toLocaleLowerCase("vi").includes(q)) return false;
      if (get("type") && (!("loai_mat_hang" in row) || row.loai_mat_hang !== get("type")))
        return false;
      if (get("person") && (!("nhan_vien_id" in row) || String(row.nhan_vien_id) !== get("person")))
        return false;
      if (get("item") && (!("mat_hang_id" in row) || String(row.mat_hang_id) !== get("item")))
        return false;
      if (
        get("receipt") &&
        (!("phieu_nhap_id" in row) || String(row.phieu_nhap_id) !== get("receipt"))
      )
        return false;
      if (
        get("request") &&
        (!("yeu_cau_san_xuat_id" in row) || String(row.yeu_cau_san_xuat_id) !== get("request"))
      )
        return false;
      if (
        get("parent") &&
        (!("lenh_san_xuat_cha_id" in row) || String(row.lenh_san_xuat_cha_id) !== get("parent"))
      )
        return false;
      if ("sku" in row) {
        if (
          (get("unit") && row.don_vi_tinh !== get("unit")) ||
          (get("color") && row.mau_sac !== get("color"))
        )
          return false;
        if (
          (get("min") && row.don_gia < Number(get("min"))) ||
          (get("max") && row.don_gia > Number(get("max")))
        )
          return false;
      } else {
        const day = localDay("posted_at" in row ? row.posted_at : row.created_at);
        if ((get("from") && day < get("from")) || (get("to") && day > get("to"))) return false;
      }
      return true;
    })
    .sort((a, b) => {
      const sort = get("sort") || (page === "mathang" ? "code" : "newest");
      if (sort === "code") return code(a).localeCompare(code(b), "vi");
      if (sort === "name" && "sku" in a && "sku" in b)
        return a.ten_mat_hang.localeCompare(b.ten_mat_hang, "vi");
      if (sort.startsWith("price") && "sku" in a && "sku" in b)
        return (sort === "price-desc" ? -1 : 1) * (a.don_gia - b.don_gia);
      const time = (r: Row) =>
        "posted_at" in r ? r.posted_at : "created_at" in r ? r.created_at : "";
      return (sort === "oldest" ? 1 : -1) * (time(a).localeCompare(time(b)) || a.id - b.id);
    });
  const invalid =
    get("from") && get("to") && get("from") > get("to")
      ? "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc."
      : get("min") && get("max") && Number(get("min")) > Number(get("max"))
        ? "Giá tối thiểu phải nhỏ hơn hoặc bằng giá tối đa."
        : "";
  const totalPages = Math.max(1, Math.ceil(rows.length / 6));
  const currentPage = Math.min(totalPages, Math.max(1, Number.parseInt(get("p")) || 1));
  const visible = rows.slice((currentPage - 1) * 6, currentPage * 6);
  const filter = (title: string, key: string, options: [string, string][]) => (
    <Field label={title}>
      <select value={get(key)} onChange={(event) => set(key, event.target.value)}>
        <option value="">Tất cả</option>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </Field>
  );
  const people: [string, string][] = Object.entries(db.names);
  const itemOptions: [string, string][] = db.items.map((x) => [String(x.id), x.ten_mat_hang]);
  const scenario = get("scenario");
  const tabs = ["", ...variants];
  return (
    <>
      <div className="op-heading">
        <div>
          <h1>{config.title}</h1>
          <p>{config.description}</p>
        </div>
        {role === "Q" && ["mathang", "dieuchinhkho"].includes(page) && (
          <Button onClick={() => open("new")}>
            {page === "mathang" ? "Thêm mặt hàng" : "Tạo phiếu điều chỉnh"}
          </Button>
        )}
      </div>
      {denied ? (
        <section className="op-empty">
          <h2>Bạn không có quyền truy cập</h2>
          <p>
            403 ·{" "}
            {role === "A"
              ? "Quản trị viên chỉ quản lý tài khoản và vai trò."
              : "Nghiệp vụ này dành cho quản lý kho."}
          </p>
          <p>Chọn vai trò khác trong phần demo để xem màn hình.</p>
        </section>
      ) : (
        <>
          <Notice>
            {page === "mathang"
              ? "Tồn kho được tính từ giao dịch đã ghi sổ. Ngừng hoạt động không xóa mặt hàng hoặc thay đổi số dư."
              : page === "giaodichkho"
                ? "Mỗi biến động đều có chứng từ nguồn. Giao dịch đã ghi sổ không được sửa hoặc xóa."
                : page === "dieuchinhkho"
                  ? "Chỉ điều chỉnh phiếu nhập đã hoàn thành. Tồn kho thay đổi khi xác nhận thành công."
                  : role === "N"
                    ? "Công việc được giao cho bạn. Chỉ bắt đầu khi đã được cấp đủ vật tư."
                    : "Lệnh được sinh từ yêu cầu sản xuất. Bắt đầu lệnh không làm thay đổi tồn kho."}
          </Notice>
          <section className="op-panel" aria-label={`Danh sách ${config.title.toLowerCase()}`}>
            <div className="op-tabs" role="tablist" aria-label="Lọc trạng thái">
              {tabs.map((value, index) => (
                <button
                  key={value}
                  id={`op-tab-${index}`}
                  role="tab"
                  aria-selected={get("status") === value}
                  aria-controls="op-results"
                  tabIndex={get("status") === value ? 0 : -1}
                  onClick={() => set("status", value)}
                  onKeyDown={(event) => {
                    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
                    event.preventDefault();
                    const next =
                      event.key === "Home"
                        ? 0
                        : event.key === "End"
                          ? tabs.length - 1
                          : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) %
                            tabs.length;
                    set("status", tabs[next]);
                    document.getElementById(`op-tab-${next}`)?.focus();
                  }}
                >
                  {value === ""
                    ? "Tất cả"
                    : value === "true"
                      ? "Hoạt động"
                      : value === "false"
                        ? "Ngừng hoạt động"
                        : label(value)}{" "}
                  <span>{base.filter((x) => !value || stateOf(x) === value).length}</span>
                </button>
              ))}
            </div>
            <div className="op-toolbar">
              <Field label={page === "giaodichkho" ? "Tìm trong dữ liệu demo" : "Tìm kiếm"}>
                <input
                  type="search"
                  placeholder={
                    page === "mathang" ? "Mã, tên hoặc SKU…" : "Mã chứng từ, tên mặt hàng…"
                  }
                  value={get("q")}
                  onChange={(event) => set("q", event.target.value)}
                />
              </Field>
              {page === "mathang" &&
                filter(
                  "Loại mặt hàng",
                  "type",
                  ["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"].map((v) => [
                    v,
                    label(v),
                  ]),
                )}
              {page === "lenhsanxuat" &&
                role === "Q" &&
                filter(
                  "Người thực hiện",
                  "person",
                  people.filter(([id]) => id !== "10"),
                )}
              {page === "giaodichkho" && filter("Mặt hàng", "item", itemOptions)}
              {page === "dieuchinhkho" &&
                filter("Phiếu nhập nguồn", "receipt", [["41", "PN-202611-000041"]])}
              <Field label="Sắp xếp">
                <select
                  value={get("sort") || (page === "mathang" ? "code" : "newest")}
                  onChange={(event) => set("sort", event.target.value)}
                >
                  {(page === "mathang"
                    ? [
                        ["code", "Mã mặt hàng"],
                        ["name", "Tên A–Z"],
                        ["price-asc", "Giá thấp đến cao"],
                        ["price-desc", "Giá cao đến thấp"],
                      ]
                    : [
                        ["newest", "Mới nhất"],
                        ["oldest", "Cũ nhất"],
                        ["code", "Mã chứng từ"],
                      ]
                  ).map(([value, text]) => (
                    <option key={value} value={value}>
                      {text}
                    </option>
                  ))}
                </select>
              </Field>
              <button
                className="op-icon"
                aria-label="Tải lại danh sách demo"
                onClick={() => set("scenario", "")}
              >
                <RefreshCw size={18} />
              </button>
            </div>
            <details className="op-advanced">
              <summary>Bộ lọc bổ sung</summary>
              <div className="op-toolbar">
                {page === "mathang" ? (
                  <>
                    {filter(
                      "Đơn vị",
                      "unit",
                      [...new Set(db.items.map((x) => x.don_vi_tinh))].map((v) => [v, label(v)]),
                    )}
                    {filter(
                      "Màu sắc",
                      "color",
                      [...new Set(db.items.map((x) => x.mau_sac))]
                        .filter(Boolean)
                        .map((v) => [v, label(v)]),
                    )}
                    {["min", "max"].map((key) => (
                      <Field key={key} label={key === "min" ? "Đơn giá từ (₫)" : "Đơn giá đến (₫)"}>
                        <input
                          type="number"
                          min="0"
                          value={get(key)}
                          onChange={(event) => set(key, event.target.value)}
                        />
                      </Field>
                    ))}
                  </>
                ) : (
                  <>
                    {page !== "lenhsanxuat" && filter("Người thực hiện", "person", people)}
                    {page === "lenhsanxuat" && (
                      <>
                        {filter("Mặt hàng đầu ra", "item", itemOptions)}
                        {filter("Yêu cầu sản xuất", "request", [
                          ["61", "YCSX-202611-000061"],
                          ["62", "YCSX-202611-000062"],
                        ])}
                        {filter(
                          "Lệnh cha",
                          "parent",
                          db.orders.map((x) => [String(x.id), x.ma_lenh_san_xuat]),
                        )}
                      </>
                    )}
                    {["from", "to"].map((key) => (
                      <Field key={key} label={key === "from" ? "Từ ngày" : "Đến ngày"}>
                        <input
                          type="date"
                          value={get(key)}
                          onChange={(event) => set(key, event.target.value)}
                        />
                      </Field>
                    ))}
                  </>
                )}
              </div>
            </details>
            <div className="op-result-summary">
              <span aria-live="polite">
                <strong>{scenario === "empty" ? 0 : rows.length}</strong> kết quả
              </span>
              <button className="op-text-button" onClick={clear}>
                Xóa bộ lọc
              </button>
            </div>
            <div
              id="op-results"
              role="tabpanel"
              aria-labelledby={`op-tab-${Math.max(0, tabs.indexOf(get("status")))}`}
            >
              {scenario === "loading" ? (
                <div className="op-empty" role="status" aria-busy="true">
                  <h2>Đang tải danh sách…</h2>
                  <p>Vui lòng chờ dữ liệu được cập nhật.</p>
                  <Button variant="secondary" onClick={() => set("scenario", "")}>
                    Kết thúc mô phỏng tải
                  </Button>
                </div>
              ) : scenario === "error" ? (
                <div className="op-empty" role="alert">
                  <h2>Chưa tải được dữ liệu</h2>
                  <p>
                    {page === "mathang"
                      ? "503 · Danh mục chưa sẵn sàng."
                      : "Kết nối bị gián đoạn. Dữ liệu chưa được cập nhật."}
                  </p>
                  <Button onClick={() => set("scenario", "")}>Thử lại</Button>
                </div>
              ) : invalid || !rows.length || scenario === "empty" ? (
                <div className="op-empty">
                  <h2>{scenario === "empty" ? "Chưa có dữ liệu" : "Không tìm thấy kết quả"}</h2>
                  <p role={invalid ? "alert" : undefined}>
                    {invalid || "Thử thay đổi từ khóa hoặc bỏ bớt bộ lọc."}
                  </p>
                  <Button variant="secondary" onClick={clear}>
                    Xem tất cả
                  </Button>
                </div>
              ) : (
                <>
                  <Table
                    headers={
                      page === "mathang"
                        ? [
                            "Mặt hàng",
                            "Loại",
                            "Đơn vị",
                            "Đơn giá (₫)",
                            "Tồn hiện tại",
                            "Trạng thái",
                            "Thao tác",
                          ]
                        : page === "lenhsanxuat"
                          ? [
                              "Lệnh sản xuất",
                              "Mặt hàng đầu ra",
                              "Đầu ra đã duyệt",
                              "Người thực hiện",
                              "Trạng thái",
                              "Thao tác",
                            ]
                          : page === "giaodichkho"
                            ? [
                                "Giao dịch / Ghi sổ",
                                "Mặt hàng",
                                "Loại giao dịch",
                                "Biến động",
                                "Chứng từ nguồn",
                                "Người thực hiện",
                                "Thao tác",
                              ]
                            : [
                                "Phiếu điều chỉnh",
                                "Phiếu nhập nguồn",
                                "Lý do",
                                "Trạng thái",
                                "Người lập",
                                "Thao tác",
                              ]
                    }
                    label={config.title}
                  >
                    {visible.map((row) => (
                      <DataRow key={row.id} row={row} open={() => open(String(row.id))} />
                    ))}
                  </Table>
                  <div className="op-pagination">
                    <span>
                      Hiển thị {(currentPage - 1) * 6 + 1}–{Math.min(currentPage * 6, rows.length)}{" "}
                      trên {rows.length}
                    </span>
                    <div>
                      <button
                        disabled={currentPage === 1}
                        onClick={() => set("p", String(currentPage - 1))}
                      >
                        Trước
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => (
                        <button
                          key={i}
                          aria-label={`Trang ${i + 1}`}
                          aria-current={currentPage === i + 1 ? "page" : undefined}
                          onClick={() => set("p", String(i + 1))}
                        >
                          {i + 1}
                        </button>
                      ))}
                      <button
                        disabled={currentPage === totalPages}
                        onClick={() => set("p", String(currentPage + 1))}
                      >
                        Sau
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>
          <div className="op-page-foot">
            <span>
              Múi giờ Việt Nam (UTC+07) ·{" "}
              {page === "giaodichkho" ? "Sổ kho chỉ đọc; biến động có dấu" : "Dữ liệu minh họa"}
            </span>
            <Field label="Xem trạng thái mẫu">
              <select value={scenario} onChange={(event) => set("scenario", event.target.value)}>
                <option value="">Có dữ liệu</option>
                <option value="empty">Chưa có dữ liệu</option>
                <option value="loading">Đang tải</option>
                <option value="error">Lỗi tải dữ liệu</option>
                <option value="conflict">Dữ liệu đã thay đổi (412)</option>
              </select>
            </Field>
          </div>
          {get("id") && (
            <Detail
              key={`${page}-${get("id")}-${role}`}
              page={page}
              id={get("id")}
              source={get("source")}
              onClose={close}
              conflict={scenario === "conflict"}
            />
          )}
        </>
      )}
    </>
  );
}
function DataRow({ row, open }: { row: Row; open: () => void }) {
  const { db } = useDemo();
  const link = (text: string) => (
    <button className="op-row-link" onClick={open}>
      {text}
    </button>
  );
  const item = "mat_hang_id" in row ? db.items.find((x) => x.id === row.mat_hang_id)! : undefined;
  return (
    <tr>
      {"sku" in row ? (
        <>
          <td>
            {link(row.ten_mat_hang)}
            <small>
              {row.ma_mat_hang} · {row.sku}
            </small>
          </td>
          <td>{label(row.loai_mat_hang)}</td>
          <td>{label(row.don_vi_tinh)}</td>
          <td className="op-num">{fmt(row.don_gia)}</td>
          <td className="op-num">
            <strong>{fmt(stock(db, row.id))}</strong>
            <small>{label(row.don_vi_tinh)}</small>
          </td>
          <td>
            <Status value={row.is_active ? "active" : "inactive"} />
          </td>
        </>
      ) : "ma_lenh_san_xuat" in row ? (
        <>
          <td>
            {link(row.ma_lenh_san_xuat)}
            <small>
              YCSX-202611-{String(row.yeu_cau_san_xuat_id).padStart(6, "0")}
              {row.lenh_san_xuat_cha_id ? " · Lệnh con" : ""}
            </small>
          </td>
          <td>
            {item?.ten_mat_hang}
            <small>{item?.ma_mat_hang}</small>
          </td>
          <td className="op-num">
            {fmt(row.so_luong_da_hoan_thanh)} / {fmt(row.so_luong)}
            <small>{label(item!.don_vi_tinh)}</small>
            <progress
              value={row.so_luong_da_hoan_thanh}
              max={row.so_luong}
              aria-label={`Đầu ra đã duyệt ${row.ma_lenh_san_xuat}`}
            />
          </td>
          <td>{db.names[row.nhan_vien_id || ""] || <span className="op-muted">Chưa giao</span>}</td>
          <td>
            <Status value={row.trang_thai} />
          </td>
        </>
      ) : "loai_giao_dich" in row ? (
        <>
          <td>
            {link(`GD-${row.id}`)}
            <small>{date(row.posted_at)}</small>
          </td>
          <td>
            {item?.ten_mat_hang}
            <small>{item?.ma_mat_hang}</small>
          </td>
          <td>
            <Status value={row.loai_giao_dich} />
          </td>
          <td className={`op-num ${row.so_luong_bien_dong < 0 ? "op-negative" : "op-positive"}`}>
            <strong>
              {row.so_luong_bien_dong > 0 ? "+" : ""}
              {fmt(row.so_luong_bien_dong)}
            </strong>
            <small>{label(item!.don_vi_tinh)}</small>
          </td>
          <td>{row.source}</td>
          <td>{db.names[row.nhan_vien_id]}</td>
        </>
      ) : (
        <>
          <td>
            {link(row.ma_phieu)}
            <small>
              {date(row.created_at)} · {row.chi_tiet.length} mặt hàng
            </small>
          </td>
          <td>PN-202611-{String(row.phieu_nhap_id).padStart(6, "0")}</td>
          <td className="op-reason">{row.ly_do}</td>
          <td>
            <Status value={row.trang_thai} />
          </td>
          <td>{db.names[row.nhan_vien_id]}</td>
        </>
      )}
      <td>{link("loai_giao_dich" in row ? "Truy vết" : "Chi tiết")}</td>
    </tr>
  );
}
