import { useState } from "react";
import { Link } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useResource } from "../../lib/api/useResources.js";
import { auditParams } from "../../lib/api/contract.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { itemName, dateTime, number } from "../../lib/format.js";
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
function AdminDashboard() {
  const attention = useResource(API.employees, { page: 1, page_size: 5, trang_thai: "bi_khoa" });
  return (
    <>
      <PageHeader
        title="Tổng quan quản trị"
        subtitle="Quản lý tài khoản, vai trò và dấu vết thao tác của hệ thống."
        action={
          <>
            <Link className="btn btn-secondary" to="/admin/lich-su">
              Xem lịch sử thao tác
            </Link>
            <Link className="btn btn-primary" to="/admin/tai-khoan/moi">
              Tạo tài khoản
            </Link>
          </>
        }
      />
      <div className="metrics">
        <Metric label="Tổng tài khoản" path={API.employees} href="/admin/tai-khoan" />
        <Metric
          label="Đang hoạt động"
          path={API.employees}
          params={{ trang_thai: "hoat_dong" }}
          href="/admin/tai-khoan"
        />
        <Metric
          label="Đang bị khóa"
          path={API.employees}
          params={{ trang_thai: "bi_khoa" }}
          href="/admin/tai-khoan"
        />
        <Metric label="Vai trò" path={API.roles} href="/admin/vai-tro" />
      </div>
      <div className="dashboard-columns">
        <Card title="Tài khoản cần chú ý" action={<Link to="/admin/tai-khoan">Xem tất cả →</Link>}>
          <QueryState query={attention}>
            <DataTable
              rows={attention.data?.data}
              empty="Không có tài khoản bị khóa."
              columns={[
                {
                  key: "ho_ten",
                  label: "Nhân viên",
                  render: (row) => (
                    <>
                      <strong>{row.ho_ten || row.ten_dang_nhap}</strong>
                      <small>{row.ma_nhan_vien}</small>
                    </>
                  ),
                },
                {
                  key: "trang_thai",
                  label: "Trạng thái",
                  render: (row) => <Badge status={row.trang_thai} />,
                },
                {
                  key: "action",
                  label: "Thao tác",
                  render: (row) => <Link to={`/admin/tai-khoan/${row.id}`}>Mở →</Link>,
                },
              ]}
            />
          </QueryState>
        </Card>
        <RecentAudit />
      </div>
    </>
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
