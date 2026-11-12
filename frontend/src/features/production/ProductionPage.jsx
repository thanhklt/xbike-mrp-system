import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider.jsx";
import { API } from "../../lib/api/endpoints.js";
import {
  useCatalog,
  useChoices,
  useCollection,
  useDetail,
  useResource,
  useWrite,
} from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { itemName, employeeName, dateTime, number } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { EmployeeSelect, statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
export function ProductionPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const base = manager ? "/kho/lenh-sx" : "/nv/lenh-sx";
  const collection = useCollection(API.orders, { sort: "-created_at" });
  const detail = useDetail(API.orders, id);
  const catalog = useCatalog();
  const employees = useChoices(API.employees, {}, manager);
  const items = catalog.data?.data || [];
  const orderStatuses = [
    ["", "Tất cả lệnh"],
    ["da_gui", "Đã giao"],
    ["dang_thuc_hien", "Đang thực hiện"],
    ["hoan_thanh", "Hoàn thành"],
  ];
  return (
    <>
      <PageHeader
        title="Lệnh sản xuất"
        subtitle={
          manager
            ? "Lệnh gốc và lệnh con được tạo khi gửi yêu cầu thành phẩm. Gán người thực hiện trước khi giao lệnh."
            : "Theo dõi vật tư, bắt đầu công việc và lập chứng từ hoàn thành cho lệnh được giao."
        }
      />
      {!manager && (
        <div className="employee-order-stats" role="group" aria-label="Lọc lệnh theo trạng thái">
          {orderStatuses.map(([status, label]) => (
            <OrderStatusCard
              key={status}
              status={status}
              label={label}
              active={(collection.params.trang_thai || "") === status}
              onClick={() => collection.filter({ trang_thai: status })}
            />
          ))}
        </div>
      )}
      <Collection
        key={!manager ? collection.params.trang_thai || "all" : "manager"}
        collection={collection}
        title={manager ? "Danh sách lệnh" : "Danh sách lệnh sản xuất"}
        searchPlaceholder={!manager ? "Tìm theo mã lệnh…" : undefined}
        filters={[
          statusFilter(["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"]),
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_lenh_san_xuat",
            label: "Mã lệnh",
            render: (row) => (
              <>
                <Link to={`${base}/${row.id}`}>{row.ma_lenh_san_xuat}</Link>
                {!manager && <small>YCSX #{row.yeu_cau_san_xuat_id}</small>}
              </>
            ),
          },
          {
            key: "mat_hang_id",
            label: "Sản phẩm",
            render: (row) => (
              <>
                {itemName(items, row.mat_hang_id)}
                <small>{manager
                  ? row.lenh_san_xuat_cha_id
                    ? `Lệnh con của #${row.lenh_san_xuat_cha_id}`
                    : "Lệnh gốc"
                  : items.find((item) => item.id === row.mat_hang_id)?.sku || "—"}</small>
              </>
            ),
          },
          {
            key: "so_luong",
            label: "Tiến độ",
            numeric: true,
            render: (row) =>
              manager ? (
                `${number(row.so_luong_da_hoan_thanh)} / ${number(row.so_luong)}`
              ) : (
                <div className="employee-progress">
                  <strong>{number(row.so_luong_da_hoan_thanh)} / {number(row.so_luong)}</strong>
                  <progress
                    max={row.so_luong}
                    value={Math.min(row.so_luong_da_hoan_thanh, row.so_luong)}
                    aria-label={`Đã hoàn thành ${row.so_luong_da_hoan_thanh} trên ${row.so_luong}`}
                  />
                </div>
              ),
          },
          {
            key: "nhan_vien_id",
            label: manager ? "Người thực hiện" : "Bắt đầu",
            render: (row) =>
              manager
                ? row.nhan_vien_id === user.id
                  ? user.ho_ten || user.ten_dang_nhap
                  : employeeName(employees.data, row.nhan_vien_id)
                : dateTime(row.started_at),
          },
          {
            key: "trang_thai",
            label: "Trạng thái",
            render: (row) => <Badge status={row.trang_thai} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (row) => <Link to={`${base}/${row.id}`}>{manager ? "Xem vật tư" : "Xem lệnh"} →</Link>,
          },
        ]}
      />
      <RecordPanel id={id} query={detail} base={base} title="Chi tiết lệnh sản xuất">
        {(snapshot) =>
          snapshot && (
            <OrderDetail
              snapshot={snapshot}
              items={items}
              employees={employees}
              base={base}
              manager={manager}
            />
          )
        }
      </RecordPanel>
    </>
  );
}
function OrderStatusCard({ status, label, active, onClick }) {
  const query = useResource(API.orders, {
    page: 1,
    page_size: 1,
    ...(status ? { trang_thai: status } : {}),
  });
  return (
    <button type="button" className="employee-order-stat" aria-pressed={active} onClick={onClick}>
      <span>{label}</span>
      <strong>{query.isError || query.isPending ? "—" : number(query.data?.meta.total)}</strong>
      {query.isError && <small>Không tải được số liệu</small>}
    </button>
  );
}
function OrderDetail({ snapshot, items, employees, base, manager }) {
  const record = snapshot.data;
  const materials = useResource(`${API.orders}/${record.id}/vat_tu`);
  const relatedCompletions = useChoices(
    API.completions,
    { lenh_san_xuat_id: record.id },
    !manager,
  );
  const pendingQuantity = relatedCompletions.data?.filter((entry) => entry.trang_thai === "cho_duyet")
    .reduce((total, entry) => total + entry.so_luong_hoan_thanh, 0);
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();
  const mutation = useWrite();
  const { save, busy, error } = useSave();
  const [assignee, setAssignee] = useState(record.nhan_vien_id || "");
  const dirty = String(assignee) !== String(record.nhan_vien_id || "");
  function action(name, title, reason = false) {
    confirm({
      title,
      description: `${record.ma_lenh_san_xuat} · ${itemName(items, record.mat_hang_id)} × ${record.so_luong}.`,
      reason,
      danger: name === "huy",
      impact:
        "Thao tác này không ghi biến động kho. Backend kiểm tra trạng thái yêu cầu và điều kiện vật tư.",
      onConfirm: async (explanation) => {
        await mutation.mutateAsync({
          path: `${API.orders}/${record.id}/${name}`,
          body: reason ? { ly_do: explanation } : {},
          etag: snapshot.etag,
        });
        notify("Đã cập nhật lệnh sản xuất.");
      },
    });
  }
  return (
    <div className="stack">
      <div className="actions">
        <h3>{record.ma_lenh_san_xuat}</h3>
        <Badge status={record.trang_thai} />
      </div>
      <InfoGrid
        entries={[
          ["Sản phẩm", itemName(items, record.mat_hang_id)],
          ["BOM đã chốt", `#${record.bom_id}`],
          [
            "Yêu cầu",
            <Link to={`${manager ? "/kho" : "/nv"}/yeu-cau/${record.yeu_cau_san_xuat_id}`}>
              YCSX #{record.yeu_cau_san_xuat_id}
            </Link>,
          ],
          [
            "Lệnh cha",
            record.lenh_san_xuat_cha_id ? (
              <Link to={`${base}/${record.lenh_san_xuat_cha_id}`}>
                #{record.lenh_san_xuat_cha_id}
              </Link>
            ) : (
              "Lệnh gốc"
            ),
          ],
          [
            "Đã hoàn thành",
            `${number(record.so_luong_da_hoan_thanh)} / ${number(record.so_luong)}`,
          ],
          ...(!manager ? [["Sản lượng chờ duyệt", pendingQuantity === undefined ? "—" : number(pendingQuantity)]] : []),
          ["Bắt đầu", dateTime(record.started_at)],
          ["Hoàn thành", dateTime(record.completed_at)],
        ]}
      />
      <div
        className="progress"
        aria-label={`Hoàn thành ${record.so_luong_da_hoan_thanh} trên ${record.so_luong}`}
      >
        <span
          style={{
            width: `${Math.min(100, (record.so_luong_da_hoan_thanh / record.so_luong) * 100)}%`,
          }}
        />
      </div>
      {record.lenh_con_ids.length > 0 && (
        <div className="actions">
          <strong>Lệnh con:</strong>
          {record.lenh_con_ids.map((child) => (
            <Link key={child} to={`${base}/${child}`}>
              #{child}
            </Link>
          ))}
        </div>
      )}
      {manager && record.trang_thai === "nhap" && (
        <QueryState query={employees}>
          <form
            className="stack"
            onSubmit={(event) => {
              event.preventDefault();
              save({
                path: `${API.orders}/${record.id}`,
                method: "patch",
                body: { nhan_vien_id: assignee ? Number(assignee) : null },
                etag: snapshot.etag,
              });
            }}
          >
            <EmployeeSelect
              employees={employees.data}
              value={assignee}
              onChange={(event) => setAssignee(event.target.value)}
              label="Người thực hiện"
            />
            <ErrorNotice error={error} />
            <Button type="submit" variant="secondary" disabled={busy || !dirty}>
              Lưu người thực hiện
            </Button>
          </form>
        </QueryState>
      )}
      <h3>Vật tư của lệnh</h3>
      <QueryState query={materials}>
        <DataTable
          caption="Vật tư của lệnh sản xuất"
          rows={materials.data?.data.chi_tiet.map((line) => ({ ...line, id: line.mat_hang_id }))}
          columns={[
            {
              key: "mat_hang_id",
              label: "Mặt hàng",
              render: (line) => itemName(items, line.mat_hang_id),
            },
            { key: "so_luong_can", label: "Cần", numeric: true },
            { key: "so_luong_da_cap", label: "Đã cấp", numeric: true },
            { key: "so_luong_con_phai_cap", label: "Còn phải cấp", numeric: true },
            { key: "ton_hien_tai", label: "Tồn hiện tại", numeric: true },
          ]}
        />
        {materials.data && (
          <Notice tone={materials.data.data.du_dieu_kien_bat_dau ? "info" : "warning"}>
            {materials.data.data.du_dieu_kien_bat_dau
              ? "Đã cấp đủ vật tư. Nhân viên có thể bắt đầu nếu lệnh đang ở trạng thái đã giao."
              : "Chưa cấp đủ vật tư; chưa thể bắt đầu sản xuất."}
          </Notice>
        )}
      </QueryState>
      {!manager && (
        <>
          <h3>Chứng từ hoàn thành liên quan</h3>
          <QueryState query={relatedCompletions}>
            <DataTable
              caption="Chứng từ hoàn thành của lệnh"
              rows={relatedCompletions.data}
              empty="Chưa có chứng từ cho lệnh này."
              columns={[
                { key: "ma_phieu", label: "Chứng từ", render: (row) => <Link to={`/nv/hoan-thanh/${row.id}`}>{row.ma_phieu}</Link> },
                { key: "so_luong_hoan_thanh", label: "Số lượng", numeric: true },
                { key: "trang_thai", label: "Trạng thái", render: (row) => <Badge status={row.trang_thai} /> },
              ]}
            />
          </QueryState>
        </>
      )}
      <div className="actions actions-end">
        {manager && record.trang_thai === "nhap" && (
          <Button
            reason={
              dirty
                ? "Lưu người thực hiện trước khi giao lệnh."
                : !record.nhan_vien_id
                  ? "Cần giao người thực hiện trước."
                  : undefined
            }
            onClick={() => action("gui", "Gửi lệnh cho nhân viên")}
          >
            Gửi lệnh
          </Button>
        )}
        {manager && !["hoan_thanh", "da_huy"].includes(record.trang_thai) && (
          <Button
            variant="secondary"
            reason={dirty ? "Lưu hoặc tải lại thay đổi trước khi hủy." : undefined}
            onClick={() => action("huy", "Hủy lệnh sản xuất", true)}
          >
            Hủy lệnh…
          </Button>
        )}
        {manager && ["da_gui", "dang_thuc_hien"].includes(record.trang_thai) && (
          <Link
            className="btn btn-secondary"
            to={`/kho/phieu-xuat/moi?loai_phieu=xuat_vat_tu&lenh_san_xuat_id=${record.id}`}
          >
            Tạo phiếu xuất vật tư
          </Link>
        )}
        {!manager && record.nhan_vien_id === user.id && record.trang_thai === "da_gui" && (
          <Button
            disabled={!materials.data?.data.du_dieu_kien_bat_dau}
            onClick={() => action("bat_dau", "Bắt đầu sản xuất")}
          >
            Bắt đầu sản xuất
          </Button>
        )}
        {!manager && record.nhan_vien_id === user.id && record.trang_thai === "dang_thuc_hien" && (
          <Link className="btn btn-primary" to={`/nv/hoan-thanh/moi?lenh_san_xuat_id=${record.id}`}>
            Tạo chứng từ hoàn thành SX
          </Link>
        )}
      </div>
    </div>
  );
}
