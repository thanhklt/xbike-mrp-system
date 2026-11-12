import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider.jsx";
import { documentPermissions } from "../auth/permissions.js";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useChoices, useCollection, useDetail } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { dateTime, localDateTime, itemName } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ApprovalActions } from "../../components/ApprovalActions.jsx";
import { statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { ErrorNotice, QueryState, Notice } from "../../components/QueryState.jsx";
export function CompletionsPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const base = manager ? "/kho/duyet-hoan-thanh" : "/nv/hoan-thanh";
  const collection = useCollection(API.completions, { sort: "-id" });
  const detail = useDetail(API.completions, id);
  const catalog = useCatalog();
  return (
    <>
      <PageHeader
        title={manager ? "Duyệt chứng từ hoàn thành SX" : "Chứng từ hoàn thành"}
        subtitle="Mỗi chứng từ ghi một đợt hoàn thành. Chỉ duyệt mới cộng đầu ra; không trừ vật tư lần nữa."
        action={
          !manager && (
            <Link className="btn btn-primary" to={`${base}/moi`}>
              Tạo chứng từ hoàn thành SX
            </Link>
          )
        }
      />
      <Collection
        collection={collection}
        title={manager ? "Danh sách chứng từ" : "Chứng từ sản xuất"}
        searchPlaceholder={!manager ? "Tìm theo mã chứng từ…" : undefined}
        filters={[statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]), ...dateFilters]}
        columns={!manager ? [
          {
            key: "ma_phieu",
            label: "Chứng từ / Lệnh",
            render: (row) => (
              <>
                <Link to={`${base}/${row.id}`}>{row.ma_phieu}</Link>
                <small>LSX #{row.lenh_san_xuat_id}</small>
              </>
            ),
          },
          { key: "mat_hang_id", label: "Thành phẩm", render: (row) => itemName(catalog.data?.data, row.mat_hang_id) },
          { key: "created_at", label: "Ngày tạo", render: (row) => dateTime(row.created_at) },
          { key: "so_luong_hoan_thanh", label: "Số lượng", numeric: true },
          { key: "trang_thai", label: "Trạng thái", render: (row) => <Badge status={row.trang_thai} /> },
          { key: "action", label: "Thao tác", render: (row) => <Link to={`${base}/${row.id}`}>Xem chi tiết →</Link> },
        ] : [
          {
            key: "ma_phieu",
            label: "Mã chứng từ",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu}</Link>,
          },
          {
            key: "mat_hang_id",
            label: "Sản phẩm",
            render: (row) => itemName(catalog.data?.data, row.mat_hang_id),
          },
          {
            key: "lenh_san_xuat_id",
            label: "Lệnh",
            render: (row) => (
              <Link to={`${manager ? "/kho" : "/nv"}/lenh-sx/${row.lenh_san_xuat_id}`}>
                #{row.lenh_san_xuat_id}
              </Link>
            ),
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
            render: (row) => <Link to={`${base}/${row.id}`}>Mở →</Link>,
          },
        ]}
      />
      <RecordPanel
        id={id}
        query={detail}
        base={base}
        title={id === "moi" ? "Tạo chứng từ hoàn thành" : "Chi tiết chứng từ hoàn thành"}
      >
        {(snapshot) => (
          <CompletionEditor snapshot={snapshot} items={catalog.data?.data || []} base={base} />
        )}
      </RecordPanel>
    </>
  );
}
function CompletionEditor({ snapshot, items, base }) {
  const record = snapshot?.data;
  const { user } = useAuth();
  const permissions = documentPermissions("completion", user.ma_vai_tro, record, user.id);
  const [search] = useSearchParams();
  const initial = {
    lenh_san_xuat_id: String(record?.lenh_san_xuat_id || search.get("lenh_san_xuat_id") || ""),
    so_luong_hoan_thanh: String(record?.so_luong_hoan_thanh || ""),
    finish_time: localDateTime(record?.finish_time || new Date()),
  };
  const [values, setValues] = useState(initial);
  const orders = useChoices(API.orders, {}, !record && permissions.create);
  const { save, busy, error } = useSave();
  const navigate = useNavigate();
  const dirty = Boolean(record && JSON.stringify(values) !== JSON.stringify(initial));
  const editable = record ? permissions.edit : permissions.create;
  const field = (name) => ({
    value: values[name],
    onChange: (event) => setValues({ ...values, [name]: event.target.value }),
  });
  function submit(event) {
    event.preventDefault();
    const body = {
      so_luong_hoan_thanh: Number(values.so_luong_hoan_thanh),
      finish_time: `${values.finish_time}:00+07:00`,
      ...(!record ? { lenh_san_xuat_id: Number(values.lenh_san_xuat_id) } : {}),
    };
    save(
      {
        path: record ? `${API.completions}/${record.id}` : API.completions,
        method: record ? "patch" : "post",
        body,
        etag: snapshot?.etag,
        versioned: Boolean(record),
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }
  if (!record && !permissions.create)
    return <Notice>Chỉ Nhân viên được giao lệnh mới có quyền lập chứng từ hoàn thành.</Notice>;
  return (
    <div className="stack">
      {record && (
        <>
          <div className="actions">
            <h3>{record.ma_phieu}</h3>
            <Badge status={record.trang_thai} />
          </div>
          <InfoGrid
            entries={[
              ["Sản phẩm", itemName(items, record.mat_hang_id)],
              ["Lệnh sản xuất", `#${record.lenh_san_xuat_id}`],
              ["Người lập", `Nhân viên #${record.nhan_vien_id}`],
              ["Tạo lúc", dateTime(record.created_at)],
            ]}
          />
        </>
      )}
      <ErrorNotice error={error} />
      {editable ? (
        <form className="stack" onSubmit={submit}>
          {!record && (
            <QueryState query={orders}>
              <Field as="select" label="Lệnh sản xuất" required {...field("lenh_san_xuat_id")}>
                <option value="">Chọn lệnh đang thực hiện</option>
                {orders.data
                  ?.filter(
                    (order) =>
                      order.nhan_vien_id === user.id && order.trang_thai === "dang_thuc_hien",
                  )
                  .map((order) => (
                    <option key={order.id} value={order.id}>
                      {order.ma_lenh_san_xuat} · {itemName(items, order.mat_hang_id)} · còn{" "}
                      {order.so_luong_con_phai_hoan_thanh}
                    </option>
                  ))}
              </Field>
            </QueryState>
          )}
          <div className="form-grid">
            <Field
              label="Số lượng hoàn thành đợt này"
              required
              type="number"
              min="1"
              max="2147483647"
              step="1"
              {...field("so_luong_hoan_thanh")}
            />
            <Field
              label="Thời điểm hoàn thành (giờ Việt Nam)"
              required
              type="datetime-local"
              {...field("finish_time")}
            />
          </div>
          <Button type="submit" disabled={busy}>
            Lưu nháp
          </Button>
        </form>
      ) : (
        <InfoGrid
          entries={[
            ["Số lượng hoàn thành", record.so_luong_hoan_thanh],
            ["Hoàn thành lúc", dateTime(record.finish_time)],
          ]}
        />
      )}
      <Notice>
        Lưu nháp và gửi duyệt chưa cộng kho. Backend kiểm tra lượng đã hoàn thành và vật tư đã cấp
        khi duyệt.
      </Notice>
      {record && (
        <ApprovalActions
          kind="completion"
          path={API.completions}
          base={base}
          snapshot={snapshot}
          items={items}
          dirty={dirty}
        />
      )}
    </div>
  );
}
