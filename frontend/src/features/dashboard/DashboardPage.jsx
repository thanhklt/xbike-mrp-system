import { useId, useState } from "react";
import { Link } from "react-router-dom";
import { Ban, BarChart3, CircleCheck, Info, Layers, PieChart, Users } from "lucide-react";
import { API } from "../../lib/api/endpoints.js";
import { useChoices, useResource } from "../../lib/api/useResources.js";
import { formatAuditAction, formatAuditDetail } from "./auditFormat.js";
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

const TRAFFIC_RANGES = [
  { key: "hom_nay", label: "Hôm nay" },
  { key: "7_ngay", label: "7 ngày" },
  { key: "30_ngay", label: "30 ngày" },
];
const TRAFFIC_MIN_Y_MAX = 4000;
const TRAFFIC_Y_STEPS = 8;
const TRAFFIC_HOURS_PER_DAY = 24;
const TRAFFIC_HOUR_LABEL_EVERY = 3;
const TRAFFIC_DAY_LABEL_EVERY = 5;
const TRAFFIC_VIEWBOX = 1000;

const trafficHourFormat = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  hour: "2-digit",
  hourCycle: "h23",
});
const trafficDayFormat = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  day: "2-digit",
  month: "2-digit",
});

function trafficTickLabel(instant, step) {
  const formatter = step === "ngay" ? trafficDayFormat : trafficHourFormat;
  const parts = Object.fromEntries(
    formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]),
  );
  // vi-VN joins day and month with "-"; the chart writes dd/MM.
  return step === "ngay" ? `${parts.day}/${parts.month}` : `${parts.hour}h`;
}

/** Points that get an x-axis label and a dot: every 3 hours, every day, or every 5 days back from today. */
function isTrafficTick(range, index, count) {
  if (range === "hom_nay") return index % TRAFFIC_HOUR_LABEL_EVERY === 0;
  if (range === "7_ngay") return true;
  return (count - 1 - index) % TRAFFIC_DAY_LABEL_EVERY === 0;
}

/** Linear axis from 0, never below the design's 4.000, rounded up to a step of 1/2/2.5/5 × 10ⁿ. */
function trafficYMax(values) {
  const highest = Math.max(0, ...values);
  if (highest <= TRAFFIC_MIN_Y_MAX) return TRAFFIC_MIN_Y_MAX;
  const rawStep = highest / TRAFFIC_Y_STEPS;
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const factor = [1, 2, 2.5, 5, 10].find((candidate) => candidate * magnitude >= rawStep);
  return factor * magnitude * TRAFFIC_Y_STEPS;
}

function trafficX(index, count) {
  return count > 1 ? (index / (count - 1)) * 100 : 0;
}

/** Monotone cubic curve (Fritsch–Carlson): smooth like the design, never dips below 0. */
function smoothTrafficPath(points) {
  if (points.length === 0) return "";
  const [first] = points;
  if (points.length === 1) return `M${first.x},${first.y}`;
  const slopes = points
    .slice(0, -1)
    .map((point, index) => (points[index + 1].y - point.y) / (points[index + 1].x - point.x));
  const tangents = points.map((_, index) => {
    if (index === 0) return slopes[0];
    if (index === points.length - 1) return slopes[index - 1];
    const before = slopes[index - 1];
    const after = slopes[index];
    return before * after <= 0 ? 0 : (before + after) / 2;
  });
  slopes.forEach((slope, index) => {
    if (slope === 0) {
      tangents[index] = 0;
      tangents[index + 1] = 0;
      return;
    }
    const a = tangents[index] / slope;
    const b = tangents[index + 1] / slope;
    const length = a * a + b * b;
    if (length > 9) {
      const scale = 3 / Math.sqrt(length);
      tangents[index] = scale * a * slope;
      tangents[index + 1] = scale * b * slope;
    }
  });
  let path = `M${first.x},${first.y}`;
  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    const third = (end.x - start.x) / 3;
    path += ` C${start.x + third},${start.y + tangents[index] * third} ${end.x - third},${
      end.y - tangents[index + 1] * third
    } ${end.x},${end.y}`;
  }
  return path;
}

function TrafficCard() {
  const gradientId = useId();
  const [range, setRange] = useState("hom_nay");
  const traffic = useResource(API.traffic, { khoang_thoi_gian: range });
  const series = traffic.isSuccess ? traffic.data?.data : null;
  const points = series?.diem ?? [];
  const count = points.length;
  const rangeLabel = TRAFFIC_RANGES.find((item) => item.key === range).label;
  const showAverage = range === "30_ngay";

  // The line stops at the last point the server has reached (later hours of today are null).
  const firstNull = points.findIndex((point) => point.so_request === null);
  const reached = firstNull === -1 ? points : points.slice(0, firstNull);
  const averages = showAverage ? points.filter((point) => point.trung_binh_7_ngay !== null) : [];
  const yMax = trafficYMax([
    ...reached.map((point) => point.so_request),
    ...averages.map((point) => point.trung_binh_7_ngay),
  ]);
  const yTicks = Array.from(
    { length: TRAFFIC_Y_STEPS + 1 },
    (_, index) => yMax - (index * yMax) / TRAFFIC_Y_STEPS,
  );
  const toSvg = (index, value) => ({
    x: (trafficX(index, count) / 100) * TRAFFIC_VIEWBOX,
    y: TRAFFIC_VIEWBOX - (value / yMax) * TRAFFIC_VIEWBOX,
  });
  const linePoints = reached.map((point) => toSvg(points.indexOf(point), point.so_request));
  const linePath = smoothTrafficPath(linePoints);
  const areaPath =
    linePoints.length > 1
      ? `${linePath} L${linePoints.at(-1).x},${TRAFFIC_VIEWBOX} L${linePoints[0].x},${TRAFFIC_VIEWBOX} Z`
      : "";
  const averagePath = smoothTrafficPath(
    averages.map((point) => toSvg(points.indexOf(point), point.trung_binh_7_ngay)),
  );

  const xTicks = series
    ? points
        .map((point, index) => ({ point, index }))
        .filter(({ index }) => isTrafficTick(range, index, count))
        .map(({ point, index }) => ({
          key: point.bat_dau,
          label: trafficTickLabel(point.bat_dau, series.buoc),
          x: trafficX(index, count),
        }))
    : range === "hom_nay"
      ? Array.from({ length: TRAFFIC_HOURS_PER_DAY / TRAFFIC_HOUR_LABEL_EVERY }, (_, slot) => ({
          key: slot,
          label: `${String(slot * TRAFFIC_HOUR_LABEL_EVERY).padStart(2, "0")}h`,
          x: trafficX(slot * TRAFFIC_HOUR_LABEL_EVERY, TRAFFIC_HOURS_PER_DAY),
        }))
      : [];
  const dots = reached
    .map((point) => ({ point, index: points.indexOf(point) }))
    .filter(({ index }) => isTrafficTick(range, index, count))
    .map(({ point, index }) => ({
      key: point.bat_dau,
      x: trafficX(index, count),
      y: (point.so_request / yMax) * 100,
    }));
  const plotLabel = series
    ? `Biểu đồ lưu lượng truy cập ${rangeLabel}: tổng ${number(series.tong_request)} request`
    : `Biểu đồ lưu lượng truy cập ${rangeLabel}`;

  return (
    <section className="admin-surface admin-traffic-card">
      <div className="admin-traffic-header">
        <div>
          <div className="admin-card-title">
            <BarChart3 size={18} className="admin-title-icon" aria-hidden="true" />
            <h2>Lưu lượng truy website</h2>
          </div>
          <p className="admin-card-subtitle">
            {range === "hom_nay"
              ? "Tổng hợp theo số lượng request mỗi giờ"
              : "Tổng hợp theo số lượng request mỗi ngày"}
          </p>
          {showAverage && (
            <ul className="admin-traffic-legend">
              <li>
                <span className="admin-traffic-legend-line" aria-hidden="true" />
                Request mỗi ngày
              </li>
              <li>
                <span className="admin-traffic-legend-line is-average" aria-hidden="true" />
                Trung bình 7 ngày
              </li>
            </ul>
          )}
          {traffic.isError && <small className="admin-stat-error">Không tải được số liệu</small>}
        </div>
        <div className="admin-range-tabs" role="group" aria-label="Khoảng thời gian lưu lượng">
          {TRAFFIC_RANGES.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`admin-range-tab${range === item.key ? " is-active" : ""}`}
              aria-pressed={range === item.key}
              onClick={() => setRange(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="admin-traffic-plot" role="img" aria-label={plotLabel}>
        <div className="admin-traffic-yaxis" aria-hidden="true">
          {yTicks.map((tick) => (
            <span key={tick}>{number(tick)}</span>
          ))}
        </div>
        <div className="admin-traffic-canvas">
          <div className="admin-traffic-gridlines" aria-hidden="true">
            {yTicks.map((tick) => (
              <div key={tick} className="admin-traffic-gridline" />
            ))}
            {linePoints.length > 0 && (
              <svg
                className="admin-traffic-svg"
                viewBox={`0 0 ${TRAFFIC_VIEWBOX} ${TRAFFIC_VIEWBOX}`}
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" className="admin-traffic-fill-top" />
                    <stop offset="100%" className="admin-traffic-fill-bottom" />
                  </linearGradient>
                </defs>
                {areaPath && <path d={areaPath} fill={`url(#${gradientId})`} />}
                <path d={linePath} className="admin-traffic-line" />
                {averagePath && <path d={averagePath} className="admin-traffic-line is-average" />}
              </svg>
            )}
            {dots.map((dot) => (
              <span
                key={dot.key}
                className="admin-traffic-dot"
                style={{ left: `${dot.x}%`, bottom: `${dot.y}%` }}
              />
            ))}
          </div>
          <div className="admin-traffic-xaxis" aria-hidden="true">
            {xTicks.map((tick) => (
              <span key={tick.key} style={{ left: `${tick.x}%` }}>
                {tick.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function AdminDashboard() {
  const employees = useChoices(API.employees);
  const logs = useResource(
    API.audit,
    auditParams({ page: 1, page_size: 5, sort: "-created_at", bo_thao_tac: "thu_hoi_quyen" }),
  );

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
        <TrafficCard />

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
