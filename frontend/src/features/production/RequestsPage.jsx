import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
import { itemName, dateTime, number } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import {
  ItemSelect,
  EmployeeSelect,
  statusFilter,
  dateFilters,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
export function RequestsPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const base = manager ? "/kho/yeu-cau" : "/nv/yeu-cau";
  const collection = useCollection(API.requests, { sort: "-created_at" });
  const detail = useDetail(API.requests, id);
  const catalog = useCatalog();
  const employees = useChoices(API.employees, {}, manager);
  const items = catalog.data?.data || [];
  return (
    <>
      <PageHeader
        title={manager ? "Yêu cầu thành phẩm" : "Yêu cầu phụ trách"}
        subtitle="Kiểm tra tồn thành phẩm, lập kế hoạch BOM nhiều cấp và theo dõi lượng đã xuất."
        action={
          manager && (
            <Link className="btn btn-primary" to={`${base}/moi`}>
              Tạo yêu cầu thành phẩm
            </Link>
          )
        }
      />
      <Collection
        collection={collection}
        filters={[
          statusFilter([
            "nhap",
            "da_gui",
            "cho_bo_sung_vat_tu",
            "dang_thuc_hien",
            "hoan_thanh",
            "da_huy",
          ]),
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_yeu_cau_san_xuat",
            label: "Mã yêu cầu",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_yeu_cau_san_xuat}</Link>,
          },
          {
            key: "mat_hang_id",
            label: "Thành phẩm",
            render: (row) => itemName(items, row.mat_hang_id),
          },
          { key: "so_luong", label: "Nhu cầu", numeric: true },
          { key: "so_luong_da_xuat", label: "Đã xuất", numeric: true },
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
        title={id === "moi" ? "Tạo yêu cầu thành phẩm" : "Chi tiết yêu cầu"}
      >
        {(snapshot) => (
          <QueryState query={catalog}>
            <RequestEditor
              snapshot={snapshot}
              items={items}
              employees={employees}
              manager={manager}
              base={base}
            />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}
function RequestEditor({ snapshot, items, employees, manager, base }) {
  const record = snapshot?.data;
  const initial = {
    mat_hang_id: String(record?.mat_hang_id || ""),
    so_luong: String(record?.so_luong || ""),
    nhan_vien_duoc_giao_id: String(record?.nhan_vien_duoc_giao_id || ""),
  };
  const [values, setValues] = useState(initial);
  const [preview, setPreview] = useState(null);
  const mutation = useWrite();
  const { save, busy, error } = useSave();
  const { confirm, notify } = useFeedback();
  const navigate = useNavigate();
  const editable = manager && (!record || record.trang_thai === "nhap");
  const dirty = JSON.stringify(values) !== JSON.stringify(initial);
  const frozen = useResource(
    `${API.requests}/${record?.id}/ke_hoach`,
    {},
    Boolean(record && record.trang_thai !== "nhap"),
  );
  const field = (name) => ({
    value: values[name],
    onChange: (event) => {
      setValues({ ...values, [name]: event.target.value });
      setPreview(null);
    },
  });
  function submit(event) {
    event.preventDefault();
    save(
      {
        path: record ? `${API.requests}/${record.id}` : API.requests,
        method: record ? "patch" : "post",
        body: {
          mat_hang_id: Number(values.mat_hang_id),
          so_luong: Number(values.so_luong),
          nhan_vien_duoc_giao_id: values.nhan_vien_duoc_giao_id
            ? Number(values.nhan_vien_duoc_giao_id)
            : null,
        },
        etag: snapshot?.etag,
        versioned: Boolean(record),
      },
      (result) => {
        setPreview(null);
        navigate(`${base}/${result.data.id}`);
      },
    );
  }
  async function calculate() {
    try {
      const result = await mutation.mutateAsync({
        path: `${API.requests}/${record.id}/tinh_ke_hoach`,
        versioned: false,
      });
      setPreview(result.data);
    } catch {
      setPreview(null);
    }
  }
  function send() {
    confirm({
      title: "Gửi yêu cầu sản xuất",
      description: `${record.ma_yeu_cau_san_xuat} · ${itemName(items, record.mat_hang_id)} × ${record.so_luong}.`,
      content: (
        <InfoGrid
          entries={[
            ["Tồn thành phẩm khi tính", preview.ton_thanh_pham],
            ["Cần sản xuất", preview.so_luong_can_san_xuat],
            ["Số lệnh dự kiến", preview.lenh_du_kien.length],
          ]}
        />
      ),
      impact:
        "Chốt kế hoạch và sinh lệnh nếu cần; chưa thay đổi tồn kho. Kế hoạch có hiệu lực 10 phút và được backend kiểm tra lại khi gửi.",
      onConfirm: async () => {
        await mutation.mutateAsync({
          path: `${API.requests}/${record.id}/gui`,
          body: { ke_hoach_token: preview.ke_hoach_token },
          etag: snapshot.etag,
        });
        setPreview(null);
        notify("Đã gửi yêu cầu và chốt kế hoạch.");
      },
    });
  }
  function cancel(remove = false) {
    confirm({
      title: remove ? "Xóa yêu cầu nháp" : "Hủy yêu cầu thành phẩm",
      description: record.ma_yeu_cau_san_xuat,
      reason: !remove,
      danger: true,
      onConfirm: async (reason) => {
        await mutation.mutateAsync({
          path: `${API.requests}/${record.id}${remove ? "" : "/huy"}`,
          method: remove ? "delete" : "post",
          body: remove ? {} : { ly_do: reason },
          etag: snapshot.etag,
        });
        notify("Đã xử lý yêu cầu.");
        if (remove) navigate(base);
      },
    });
  }
  if (!record && !manager) return <Notice>Bạn chỉ có thể xem yêu cầu được giao.</Notice>;
  return (
    <div className="stack">
      {record && (
        <>
          <div className="actions">
            <h3>{record.ma_yeu_cau_san_xuat}</h3>
            <Badge status={record.trang_thai} />
          </div>
          <InfoGrid
            entries={[
              [
                "Đã xuất / yêu cầu",
                `${number(record.so_luong_da_xuat)} / ${number(record.so_luong)}`,
              ],
              ["Còn phải xuất", number(record.so_luong_con_phai_xuat)],
              ["Tạo lúc", dateTime(record.created_at)],
              ["Hoàn thành lúc", dateTime(record.completed_at)],
            ]}
          />
        </>
      )}
      <ErrorNotice error={error || mutation.error} />
      {editable ? (
        <QueryState query={employees}>
          <form className="stack" onSubmit={submit}>
            <div className="form-grid">
              <ItemSelect
                label="Thành phẩm"
                required
                items={items}
                types={["thanh_pham"]}
                {...field("mat_hang_id")}
              />
              <Field
                label="Số lượng cần"
                type="number"
                required
                min="1"
                step="1"
                max="2147483647"
                {...field("so_luong")}
              />
            </div>
            <EmployeeSelect employees={employees.data} {...field("nhan_vien_duoc_giao_id")} />
            <Button type="submit" disabled={busy}>
              Lưu nháp
            </Button>
          </form>
        </QueryState>
      ) : (
        <InfoGrid
          entries={[
            ["Thành phẩm", itemName(items, record.mat_hang_id)],
            [
              "Người phụ trách",
              record.nhan_vien_duoc_giao_id
                ? `Nhân viên #${record.nhan_vien_duoc_giao_id}`
                : "Chưa giao",
            ],
          ]}
        />
      )}
      {record && editable && (
        <div className="actions">
          <Button
            variant="secondary"
            reason={dirty ? "Lưu thay đổi trước khi tính kế hoạch." : undefined}
            disabled={mutation.isPending}
            onClick={calculate}
          >
            {preview ? "Tính lại" : "Tính kế hoạch"}
          </Button>
          <Button
            reason={
              dirty
                ? "Lưu thay đổi và tính lại kế hoạch."
                : !preview
                  ? "Cần tính kế hoạch trước khi gửi."
                  : !preview.du_dieu_kien_gui
                    ? "Chưa đủ điều kiện gửi; kiểm tra BOM và người phụ trách."
                    : undefined
            }
            onClick={send}
          >
            Gửi yêu cầu cho nhân viên
          </Button>
          <Button
            variant="secondary"
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước." : undefined}
            onClick={() => cancel(true)}
          >
            Xóa nháp
          </Button>
        </div>
      )}
      {preview && (
        <>
          <InfoGrid
            entries={[
              ["Tồn thành phẩm", preview.ton_thanh_pham],
              ["Cần sản xuất", preview.so_luong_can_san_xuat],
              ["Tính lúc", dateTime(preview.tinh_luc)],
            ]}
          />
          {preview.thieu_vat_tu && (
            <Notice tone="warning">
              Kế hoạch có vật tư thiếu. Gửi yêu cầu sẽ chuyển sang chờ bổ sung vật tư theo kết quả
              backend; chưa giữ chỗ hoặc thay đổi kho.
            </Notice>
          )}
          <h3>Vật tư dự kiến</h3>
          <DataTable
            rows={preview.vat_tu.map((line) => ({ ...line, id: line.mat_hang_id }))}
            columns={[
              { key: "ten_mat_hang", label: "Vật tư" },
              { key: "so_luong_can_tu_kho", label: "Cần từ kho", numeric: true },
              { key: "so_luong_hien_co", label: "Hiện có", numeric: true },
              { key: "so_luong_thieu", label: "Thiếu", numeric: true },
            ]}
          />
          <h3>Cây lệnh dự kiến</h3>
          <OrderTree orders={preview.lenh_du_kien} items={items} temporary />
        </>
      )}
      {record && record.trang_thai !== "nhap" && (
        <>
          <h3>Kế hoạch đã chốt</h3>
          <QueryState query={frozen}>
            <OrderTree
              orders={frozen.data?.data.lenh || []}
              items={items}
              prefix={manager ? "/kho" : "/nv"}
            />
          </QueryState>
        </>
      )}
      {manager && record && !["hoan_thanh", "da_huy"].includes(record.trang_thai) && (
        <div className="actions">
          <Button
            variant="secondary"
            reason={dirty ? "Lưu hoặc tải lại trước khi hủy." : undefined}
            onClick={() => cancel()}
          >
            Hủy yêu cầu…
          </Button>
          {!["nhap", "cho_bo_sung_vat_tu"].includes(record.trang_thai) && (
            <Link
              className="btn btn-secondary"
              to={`/kho/phieu-xuat/moi?loai_phieu=xuat_thanh_pham&yeu_cau_san_xuat_id=${record.id}`}
            >
              Tạo phiếu xuất thành phẩm
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
function OrderTree({ orders, items, prefix, temporary = false, parent = null }) {
  const nodes = orders.filter(
    (order) => (temporary ? order.ma_cha_tam : order.lenh_san_xuat_cha_id) === parent,
  );
  if (!orders.length) return <Notice>Không có lệnh sản xuất trong kế hoạch.</Notice>;
  return (
    <ul className="tree">
      {nodes.map((order) => {
        const id = temporary ? order.ma_tam : order.id;
        return (
          <li key={id}>
            {temporary ? (
              <strong>{order.ma_tam}</strong>
            ) : (
              <Link to={`${prefix}/lenh-sx/${id}`}>{order.ma_lenh_san_xuat}</Link>
            )}{" "}
            · {itemName(items, order.mat_hang_id)} × {order.so_luong} · BOM #
            {order.bom_id || "chưa có"}
            {!temporary && <Badge status={order.trang_thai} />}
            {orders.some(
              (child) => (temporary ? child.ma_cha_tam : child.lenh_san_xuat_cha_id) === id,
            ) && (
              <OrderTree
                orders={orders}
                items={items}
                prefix={prefix}
                temporary={temporary}
                parent={id}
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}
