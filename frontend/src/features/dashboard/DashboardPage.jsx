import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Ban,
  BarChart3,
  CircleCheck,
  Info,
  Layers,
  PieChart,
  Users,
} from "lucide-react";
import { API } from "../../lib/api/endpoints.js";
import { useChoices, useResource } from "../../lib/api/useResources.js";
import { auditParams } from "../../lib/api/contract.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import {
  ROLE_LABELS,
  dateTime,
  employeeName,
  formatAuditTime,
  itemName,
  number,
} from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { QueryState } from "../../components/QueryState.jsx";

export function DashboardPage() {
  const { user } = useAuth();
  if (user.ma_vai_tro === "quan_tri_vien") return <AdminDashboard />;
  if (user.ma_vai_tro === "quan_ly") return <WarehouseDashboard />;
  return <EmployeeDashboard />;
}

function Metric({ label, path, params, href }) {
  const query = useResource(path, { page: 1, page_size: 1, ...params });
  return (
    <Link className="metric" to={href}>
      <span>{label}</span>
      <strong>{query.isError || query.isPending ? "—" : number(query.data?.meta.total)}</strong>
      {query.isError && <small>Không tải được số liệu</small>}
    </Link>
  );
}

const AUDIT_ACTION_LABELS = {
  tao: "Tạo",
  sua: "Cập nhật",
  xoa_nhap: "Xóa nháp",
  gui: "Gửi",
  bat_dau: "Bắt đầu",
  duyet: "Duyệt",
  tu_choi: "Từ chối",
  ve_nhap: "Chuyển về nháp",
  hoan_tat: "Hoàn tất",
  cap_quyen: "Cấp quyền",
  thu_hoi_quyen: "Thu hồi quyền",
  vo_hieu_hoa: "Vô hiệu hóa",
  huy: "Hủy",
  ghi_nhan_loi: "Ghi nhận lỗi",
  nhan_xu_ly: "Nhận xử lý",
  giai_quyet: "Giải quyết",
  xac_nhan: "Xác nhận",
};

const AUDIT_OBJECT_LABELS = {
  nhan_vien: "tài khoản",
  vai_tro: "vai trò",
  mat_hang: "mặt hàng",
  nha_cung_cap: "nhà cung cấp",
  cong_thuc: "BOM",
  phieu_nhap: "phiếu nhập",
  phieu_xuat: "phiếu xuất",
  yeu_cau_san_xuat: "yêu cầu sản xuất",
  lenh_san_xuat: "lệnh sản xuất",
  chung_tu_hoan_thanh_san_xuat: "chứng từ hoàn thành SX",
  phieu_dieu_chinh_kho: "phiếu điều chỉnh kho",
  ticket_loi_dieu_chinh: "ticket lỗi điều chỉnh",
};

function formatAuditAction(entry) {
  const verb = AUDIT_ACTION_LABELS[entry.thao_tac] || entry.thao_tac;
  const noun = AUDIT_OBJECT_LABELS[entry.loai_doi_tuong] || entry.loai_doi_tuong;
  return `${verb} ${noun}`;
}

function formatAuditDetail(entry, employees = []) {
  const objectLabel = AUDIT_OBJECT_LABELS[entry.loai_doi_tuong] || entry.loai_doi_tuong;
  let target = `${objectLabel} #${entry.doi_tuong_id}`;
  if (entry.loai_doi_tuong === "nhan_vien") {
    const matched = employees.find((item) => item.id === Number(entry.doi_tuong_id));
    if (matched) {
      target = `${matched.ma_nhan_vien}${matched.ho_ten ? ` (${matched.ho_ten})` : ""}`;
    }
  }
  return entry.ly_do ? `${target} · ${entry.ly_do}` : target;
}

function AdminStatCard({ label, icon, tone, path, params, href }) {
  const IconComponent = icon;
  const query = useResource(path, { page: 1, page_size: 1, ...params });
  const value = query.isError || query.isPending ? "—" : number(query.data?.meta.total);
  return (
    <Link className="admin-stat-card" to={href}>
      <span className={`admin-stat-icon admin-stat-${tone}`} aria-hidden="true">
        <IconComponent size={28} strokeWidth={2.15} />
      </span>
      <div className="admin-stat-copy">
        <span className="admin-stat-label">{label}</span>
        <strong className="admin-stat-value">{value}</strong>
        {query.isError && <small className="admin-stat-error">Không tải được số liệu</small>}
      </div>
    </Link>
  );
}

const ROLE_CHART_CONFIG = [
  { code: "nhan_vien", label: "Nhân viên", color: "#e86a19" },
  { code: "quan_ly", label: "Quản lý kho", color: "#fda965" },
  { code: "quan_tri_vien", label: "Quản trị viên", color: "#feddbe" },
];

const TRAFFIC_TICKS_Y = ["4.000", "3.500", "3.000", "2.500", "2.000", "1.000", "500", "0"];
const TRAFFIC_TICKS_X = ["00h", "03h", "06h", "09h", "12h", "15h", "18h", "21h"];

function AdminDashboard() {
  const employees = useChoices(API.employees);
  const logs = useResource(API.audit, auditParams({ page: 1, page_size: 5, sort: "-created_at" }));

  const employeeRows = employees.data || [];
  const totalAccounts = employeeRows.length;
  const radius = 84;
  const circumference = 2 * Math.PI * radius;

  let cumulativeOffset = 0;
  const distribution = ROLE_CHART_CONFIG.map((item) => {
    const count = employeeRows.filter((person) => person.ma_vai_tro === item.code).length;
    const ratio = totalAccounts > 0 ? count / totalAccounts : 0;
    const percentage = (ratio * 100).toFixed(1);
    const dashLength = ratio * circumference;
    const segment = {
      ...item,
      count,
      percentage,
      dashArray: `${dashLength} ${Math.max(circumference - dashLength, 0)}`,
      dashOffset: -cumulativeOffset,
    };
    cumulativeOffset += dashLength;
    return segment;
  });

  return (
    <div className="admin-screen">
      <div className="admin-page-heading">
        <h1>Tổng quan</h1>
      </div>

      <div className="admin-stats-grid">
        <AdminStatCard
          label="Tổng tài khoản"
          icon={Users}
          tone="amber"
          path={API.employees}
          href="/admin/tai-khoan"
        />
        <AdminStatCard
          label="Tổng vai trò"
          icon={Layers}
          tone="blue"
          path={API.roles}
          href="/admin/vai-tro"
        />
        <AdminStatCard
          label="Tài khoản đang hoạt động"
          icon={CircleCheck}
          tone="green"
          path={API.employees}
          params={{ trang_thai: "hoat_dong" }}
          href="/admin/tai-khoan"
        />
        <AdminStatCard
          label="Tài khoản đã vô hiệu hóa"
          icon={Ban}
          tone="red"
          path={API.employees}
          params={{ trang_thai: "bi_khoa" }}
          href="/admin/tai-khoan"
        />
      </div>

      <div className="admin-charts-row">
        <section className="admin-surface admin-traffic-card">
          <div className="admin-traffic-header">
            <div>
              <div className="admin-card-title">
                <BarChart3 size={18} className="admin-title-icon" aria-hidden="true" />
                <h2>Lưu lượng truy website</h2>
              </div>
              <p className="admin-card-subtitle">Tổng hợp theo số lượng request mỗi giờ</p>
            </div>
            <div className="admin-range-tabs" role="group" aria-label="Khoảng thời gian lưu lượng">
              <button type="button" className="admin-range-tab is-active">
                Hôm nay
              </button>
              <button type="button" className="admin-range-tab">
                7 ngày
              </button>
              <button type="button" className="admin-range-tab">
                30 ngày
              </button>
            </div>
          </div>

          <div
            className="admin-traffic-plot"
            role="img"
            aria-label="Khung biểu đồ lưu lượng truy cập theo giờ"
          >
            <div className="admin-traffic-yaxis" aria-hidden="true">
              {TRAFFIC_TICKS_Y.map((tick) => (
                <span key={tick}>{tick}</span>
              ))}
            </div>
            <div className="admin-traffic-canvas">
              <div className="admin-traffic-gridlines" aria-hidden="true">
                {TRAFFIC_TICKS_Y.map((tick) => (
                  <div key={tick} className="admin-traffic-gridline" />
                ))}
              </div>
              <div className="admin-traffic-xaxis" aria-hidden="true">
                {TRAFFIC_TICKS_X.map((tick) => (
                  <span key={tick}>{tick}</span>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="admin-surface admin-donut-card">
          <div className="admin-card-title">
            <PieChart size={18} className="admin-title-icon" aria-hidden="true" />
            <h2>Phân bổ tài khoản theo vai trò</h2>
          </div>

          <QueryState query={employees}>
            <div className="admin-donut-layout">
              <div className="admin-donut-figure">
                <svg
                  viewBox="0 0 216 216"
                  className="admin-donut-svg"
                  role="img"
                  aria-label="Biểu đồ phân bổ tài khoản theo vai trò"
                >
                  <circle
                    cx="108"
                    cy="108"
                    r={radius}
                    fill="none"
                    stroke="#2d2621"
                    strokeWidth="30"
                  />
                  {distribution.map(
                    (segment) =>
                      segment.count > 0 && (
                        <circle
                          key={segment.code}
                          cx="108"
                          cy="108"
                          r={radius}
                          fill="none"
                          stroke={segment.color}
                          strokeWidth="30"
                          strokeDasharray={segment.dashArray}
                          strokeDashoffset={segment.dashOffset}
                          transform="rotate(-90 108 108)"
                        />
                      ),
                  )}
                </svg>
                <div className="admin-donut-center">
                  <strong>{number(totalAccounts)}</strong>
                  <span>Tài khoản</span>
                </div>
              </div>

              <ul className="admin-donut-legend">
                {distribution.map((segment) => (
                  <li key={segment.code}>
                    <span
                      className="admin-legend-swatch"
                      style={{ backgroundColor: segment.color }}
                      aria-hidden="true"
                    />
                    <span className="admin-legend-text">
                      {ROLE_LABELS[segment.code] || segment.label}:{" "}
                      <strong>
                        {number(segment.count)} ({segment.percentage}%)
                      </strong>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </QueryState>
        </section>
      </div>

      <section className="admin-surface admin-activity-card">
        <div className="admin-card-title">
          <Info size={18} className="admin-title-icon" aria-hidden="true" />
          <h2>Hoạt động gần đây</h2>
        </div>

        <QueryState query={logs}>
          <div className="table-scroll admin-table-wrap">
            <table className="admin-table">
              <caption className="sr-only">Hoạt động gần đây</caption>
              <thead>
                <tr>
                  <th scope="col">Thời gian</th>
                  <th scope="col">Người thực hiện</th>
                  <th scope="col">Hành động</th>
                  <th scope="col">Chi tiết</th>
                </tr>
              </thead>
              <tbody>
                {logs.data?.data?.length ? (
                  logs.data.data.map((entry) => (
                    <tr key={entry.id}>
                      <td>{formatAuditTime(entry.created_at)}</td>
                      <td>
                        <strong>{employeeName(employeeRows, entry.nhan_vien_id)}</strong>
                      </td>
                      <td>{formatAuditAction(entry)}</td>
                      <td>{formatAuditDetail(entry, employeeRows)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="empty-state">
                      Chưa có lịch sử thao tác.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </QueryState>
      </section>
    </div>
  );
}
function WarehouseDashboard() {
  const pending = useResource(API.completions, { page: 1, page_size: 5, trang_thai: "cho_duyet" });
  return (
    <>
      <PageHeader
        title="Tổng quan kho & sản xuất"
        subtitle="Theo dõi công việc cần xử lý và tra cứu tồn kho hiện tại."
        action={
          <>
            <Link className="btn btn-primary" to="/kho/phieu-nhap/moi">
              Tạo phiếu nhập
            </Link>
            <Link className="btn btn-secondary" to="/kho/yeu-cau/moi">
              Tạo yêu cầu thành phẩm
            </Link>
          </>
        }
      />
      <div className="metrics">
        <Metric
          label="Yêu cầu đã gửi"
          path={API.requests}
          params={{ trang_thai: "da_gui" }}
          href="/kho/yeu-cau"
        />
        <Metric
          label="Lệnh đang thực hiện"
          path={API.orders}
          params={{ trang_thai: "dang_thuc_hien" }}
          href="/kho/lenh-sx"
        />
        <Metric
          label="Chờ bổ sung vật tư"
          path={API.requests}
          params={{ trang_thai: "cho_bo_sung_vat_tu" }}
          href="/kho/yeu-cau"
        />
        <Metric
          label="Hoàn thành chờ duyệt"
          path={API.completions}
          params={{ trang_thai: "cho_duyet" }}
          href="/kho/duyet-hoan-thanh"
        />
      </div>
      <Card
        title="Chứng từ hoàn thành cần duyệt"
        action={<Link to="/kho/duyet-hoan-thanh">Xem tất cả →</Link>}
      >
        <QueryState query={pending}>
          <DataTable
            rows={pending.data?.data}
            empty="Không có chứng từ hoàn thành chờ duyệt."
            columns={[
              { key: "ma_phieu", label: "Chứng từ" },
              {
                key: "lenh_san_xuat_id",
                label: "Lệnh sản xuất",
                render: (row) => `#${row.lenh_san_xuat_id}`,
              },
              { key: "so_luong_hoan_thanh", label: "Số lượng", numeric: true },
              {
                key: "finish_time",
                label: "Hoàn thành lúc",
                render: (row) => dateTime(row.finish_time),
              },
              {
                key: "trang_thai",
                label: "Trạng thái",
                render: (row) => <Badge status={row.trang_thai} />,
              },
              {
                key: "action",
                label: "Thao tác",
                render: (row) => <Link to={`/kho/duyet-hoan-thanh/${row.id}`}>Xem & duyệt →</Link>,
              },
            ]}
          />
        </QueryState>
      </Card>
      <div className="dashboard-columns">
        <QuickStock />
        <RecentAudit />
      </div>
    </>
  );
}
function EmployeeDashboard() {
  const orders = useResource(API.orders, { page: 1, page_size: 5, trang_thai: "da_gui" });
  const items = useResource(API.catalog);
  return (
    <>
      <PageHeader
        title="Tổng quan"
        subtitle="Yêu cầu phụ trách, lệnh của bạn và chứng từ cần theo dõi."
        action={
          <Link className="btn btn-primary" to="/nv/hoan-thanh/moi">
            Tạo chứng từ hoàn thành SX
          </Link>
        }
      />
      <div className="metrics">
        <Metric label="Yêu cầu phụ trách" path={API.requests} href="/nv/yeu-cau" />
        <Metric
          label="Lệnh đã giao"
          path={API.orders}
          params={{ trang_thai: "da_gui" }}
          href="/nv/lenh-sx"
        />
        <Metric
          label="Đang thực hiện"
          path={API.orders}
          params={{ trang_thai: "dang_thuc_hien" }}
          href="/nv/lenh-sx"
        />
        <Metric
          label="Hoàn thành chờ duyệt"
          path={API.completions}
          params={{ trang_thai: "cho_duyet" }}
          href="/nv/hoan-thanh"
        />
      </div>
      <Card title="Lệnh chờ bắt đầu" action={<Link to="/nv/lenh-sx">Xem lệnh của tôi →</Link>}>
        <QueryState query={orders}>
          <DataTable
            rows={orders.data?.data}
            empty="Không có lệnh chờ bắt đầu."
            columns={[
              {
                key: "ma_lenh_san_xuat",
                label: "Mã lệnh",
                render: (row) => <Link to={`/nv/lenh-sx/${row.id}`}>{row.ma_lenh_san_xuat}</Link>,
              },
              {
                key: "mat_hang_id",
                label: "Sản phẩm",
                render: (row) => itemName(items.data?.data, row.mat_hang_id),
              },
              { key: "so_luong", label: "Số lượng", numeric: true },
              {
                key: "trang_thai",
                label: "Trạng thái",
                render: (row) => <Badge status={row.trang_thai} />,
              },
              {
                key: "action",
                label: "Thao tác",
                render: (row) => <Link to={`/nv/lenh-sx/${row.id}`}>Xem vật tư →</Link>,
              },
            ]}
          />
        </QueryState>
      </Card>
      <div className="dashboard-columns">
        <QuickStock />
        <Card title="Theo dõi công việc">
          <div className="stack">
            <p className="muted">
              Phiếu xuất do Quản lý kho lập và duyệt. Bạn được xem các phiếu liên quan và lập chứng
              từ hoàn thành cho lệnh của mình.
            </p>
            <Link to="/nv/xuat-nvl">Xem phiếu xuất vật tư →</Link>
            <Link to="/nv/xuat-tp">Xem phiếu xuất thành phẩm →</Link>
            <Link to="/nv/phieu">Theo dõi chứng từ của tôi →</Link>
          </div>
        </Card>
      </div>
    </>
  );
}
function QuickStock() {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const stock = useResource(API.items, { page: 1, page_size: 5, q: query });
  return (
    <Card title="Tra cứu tồn kho nhanh">
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(draft.trim());
        }}
      >
        <Field
          label="Tìm mã hoặc tên mặt hàng"
          type="search"
          placeholder="Tìm mã / tên mặt hàng…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <Button variant="secondary" type="submit">
          Tìm
        </Button>
      </form>
      <QueryState query={stock}>
        <div className="compact-list">
          {stock.data?.data.length ? (
            stock.data.data.map((item) => (
              <div className="compact-row" key={item.id}>
                <div>
                  <strong>{item.ten_mat_hang}</strong>
                  <small>{item.ma_mat_hang}</small>
                </div>
                <strong>
                  {number(item.so_luong_ton)} {item.don_vi_tinh}
                </strong>
              </div>
            ))
          ) : (
            <p className="empty-state">Không có mặt hàng phù hợp.</p>
          )}
        </div>
      </QueryState>
      <small className="muted">
        NVL = Nguyên vật liệu · BTP = Bán thành phẩm · TP = Thành phẩm
      </small>
    </Card>
  );
}
function RecentAudit() {
  const logs = useResource(API.audit, auditParams({ page: 1, page_size: 5, sort: "-created_at" }));
  return (
    <Card title="Hoạt động gần đây">
      <QueryState query={logs}>
        <div className="compact-list">
          {logs.data?.data.length ? (
            logs.data.data.map((entry) => (
              <div className="compact-row" key={entry.id}>
                <div>
                  <small>
                    {dateTime(entry.created_at)} · Nhân viên #{entry.nhan_vien_id}
                  </small>
                  <p>
                    {entry.thao_tac} · {entry.loai_doi_tuong} #{entry.doi_tuong_id}
                  </p>
                  {entry.ly_do && <small>{entry.ly_do}</small>}
                </div>
              </div>
            ))
          ) : (
            <p className="empty-state">Chưa có lịch sử thao tác.</p>
          )}
        </div>
      </QueryState>
    </Card>
  );
}
