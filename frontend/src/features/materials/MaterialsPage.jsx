import { useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import {
  ITEM_LABELS,
  money,
  number,
  dateTime,
  unitLabel,
  colorLabel,
  quantity,
} from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { AdminStatusBadge, Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ErrorNotice, QueryState } from "../../components/QueryState.jsx";
import { DocumentLines, newLine, itemTypeOptions } from "../../components/ResourceFields.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import { itemPayload, itemUnitOptions } from "./itemForm.js";

const warehouseTypes = [
  { value: "", label: "Tất cả" },
  { value: "linh_kien", label: "Linh kiện" },
  { value: "thanh_pham", label: "Thành phẩm" },
];
const modes = {
  manage: { base: "/kho/mat-hang", title: "Mặt hàng và tồn kho", showPrice: true },
  employee: { base: "/nv/ton-kho", title: "Tra cứu tồn kho", showPrice: false },
  admin: { base: "/admin/mat-hang", title: "Tra cứu mặt hàng", showPrice: true },
};

export function MaterialsPage({ mode = "manage" }) {
  const { base, title, showPrice } = modes[mode];
  const readOnly = mode !== "manage";
  const invalidStatusMessage = mode === "admin"
    ? "Trạng thái chỉ lọc được cho thành phẩm."
    : "Linh kiện không có trạng thái";
  const { id } = useParams();
  const collection = useCollection(API.items, { sort: readOnly ? "id" : "ma_mat_hang" });
  const detail = useDetail(API.items, id);
  if (readOnly && id === "moi") return <Navigate to={base} replace />;
  return (
    <>
      {mode === "admin" ? (
        <PageHeader variant="large" title={title} />
      ) : (
        <PageHeader
          title={title}
          subtitle={mode === "employee" ? undefined : "Linh kiện · Thành phẩm. Tồn kho chỉ thay đổi qua chứng từ đã ghi sổ."}
          action={
            !readOnly && (
              <Link className="btn btn-primary" to={`${base}/moi`}>
                Thêm mặt hàng
              </Link>
            )
          }
        />
      )}
      <div className={mode === "employee" ? "employee-inventory" : undefined}>
        <Collection
          collection={collection}
          title={mode === "employee" ? "Danh sách tồn kho" : "Danh sách"}
          filterIcon={mode === "employee"}
          cycleFilters={mode === "employee"}
          searchPlaceholder={mode === "employee" ? "Tìm mã hoặc tên mặt hàng…" : undefined}
          allowReset={!readOnly}
          pageSizes={readOnly ? undefined : [20, 50, 100]}
          validate={(draft) =>
            draft.loai_mat_hang === "linh_kien" && (draft.is_active ?? "") !== ""
              ? invalidStatusMessage
              : null
          }
          filters={[
            {
              name: "loai_mat_hang",
              label: "Loại mặt hàng",
              as: "select",
              options: readOnly
                ? itemTypeOptions.filter(({ value }) => ["", "linh_kien", "thanh_pham"].includes(value))
                : warehouseTypes,
            },
            {
              name: "is_active",
              label: "Trạng thái",
              as: "select",
              options: [
                { value: "", label: "Tất cả" },
                { value: "true", label: "Đang dùng" },
                { value: "false", label: "Ngừng dùng" },
              ],
            },
            {
              name: "sort",
              label: "Sắp xếp",
              as: "select",
              options: readOnly
                ? [
                    { value: "id", label: "ID tăng dần" },
                    { value: "ten_mat_hang", label: "Tên mặt hàng" },
                    { value: "-don_gia", label: "Đơn giá giảm dần" },
                  ]
                : [
                    { value: "ma_mat_hang", label: "Mã tăng dần" },
                    { value: "-ma_mat_hang", label: "Mã giảm dần" },
                    { value: "don_gia", label: "Đơn giá tăng dần" },
                    { value: "-don_gia", label: "Đơn giá giảm dần" },
                  ],
            },
          ]}
          columns={[
            {
              key: "ma_mat_hang",
              label: mode === "employee" ? "Mã hàng / SKU" : "Mã",
              render: (row) => mode === "employee" ? (
                <>
                  <Link to={`${base}/${row.id}`}>{row.sku}</Link>
                  <small>{row.ma_mat_hang}</small>
                </>
              ) : <Link to={`${base}/${row.id}`}>{row.ma_mat_hang}</Link>,
            },
            {
              key: "ten_mat_hang",
              label: "Tên mặt hàng",
              render: (row) => (
                <>
                  <strong>{row.ten_mat_hang}</strong>
                  <small>{ITEM_LABELS[row.loai_mat_hang]}</small>
                </>
              ),
            },
            ...(mode !== "employee" ? [{ key: "sku", label: "SKU" }] : []),
            ...(mode === "employee" ? [{ key: "loai_mat_hang", label: "Loại", render: (row) => ITEM_LABELS[row.loai_mat_hang] }] : []),
            {
              key: "so_luong_ton",
              label: readOnly ? "Tồn kho" : "Tồn thực tế",
              numeric: true,
              render: (row) => (
                <>
                  {number(row.so_luong_ton)}
                  <small>{unitLabel(row.don_vi_tinh)}</small>
                </>
              ),
            },
            ...(!readOnly
              ? [
                  {
                    key: "so_luong_dang_giu",
                    label: "Đang giữ",
                    numeric: true,
                    render: (row) => number(row.so_luong_dang_giu),
                  },
                  {
                    key: "so_luong_con_dung",
                    label: "Còn dùng",
                    numeric: true,
                    render: (row) => number(row.so_luong_con_dung),
                  },
                ]
              : []),
            ...(showPrice
              ? [
                  {
                    key: "don_gia",
                    label: "Đơn giá",
                    numeric: true,
                    render: (row) => money(row.don_gia),
                  },
                ]
              : []),
            {
              key: "is_active",
              label: "Trạng thái",
              render: (row) => {
                if (mode !== "admin" && row.loai_mat_hang === "linh_kien") return "—";
                const StatusBadge = mode === "admin" ? AdminStatusBadge : Badge;
                return (
                  <StatusBadge status={row.is_active ? "hoat_dong" : "bi_khoa"}>
                    {row.is_active ? "Đang dùng" : "Ngừng dùng"}
                  </StatusBadge>
                );
              },
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => (
                <Link
                  className={readOnly ? undefined : "warehouse-item-edit"}
                  to={`${base}/${row.id}`}
                >
                  {mode === "employee" ? "Xem" : readOnly ? "Xem →" : "Sửa →"}
                </Link>
              ),
            },
          ]}
        />
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Thêm mặt hàng" : "Chi tiết mặt hàng"}
        >
          {(snapshot) =>
            mode === "admin" ? (
              <InfoGrid
                entries={[
                  ["Mã", snapshot.data.ma_mat_hang],
                  ["Tên mặt hàng", snapshot.data.ten_mat_hang],
                  ["Loại", ITEM_LABELS[snapshot.data.loai_mat_hang]],
                  ["SKU", snapshot.data.sku],
                  ["Đơn vị tính", unitLabel(snapshot.data.don_vi_tinh)],
                  ["Đơn giá", money(snapshot.data.don_gia)],
                  ["Màu sắc", colorLabel(snapshot.data.mau_sac)],
                  ["Mô tả", snapshot.data.mo_ta],
                  ["Trạng thái", snapshot.data.is_active ? "Đang dùng" : "Ngừng dùng"],
                  [
                    "Tồn thực tế",
                    quantity(snapshot.data.so_luong_ton, snapshot.data.don_vi_tinh),
                  ],
                  [
                    "Đang giữ",
                    quantity(snapshot.data.so_luong_dang_giu, snapshot.data.don_vi_tinh),
                  ],
                  [
                    "Còn dùng được",
                    quantity(snapshot.data.so_luong_con_dung, snapshot.data.don_vi_tinh),
                  ],
                  ["Cập nhật tồn", dateTime(snapshot.data.ton_kho_updated_at)],
                ]}
              />
            ) : readOnly ? (
              <InfoGrid
                entries={[
                  ["Mã hàng", snapshot?.data.sku],
                  ["Loại hàng", ITEM_LABELS[snapshot?.data.loai_mat_hang]],
                  ["Tồn kho hiện tại", `${number(snapshot?.data.so_luong_ton)} ${unitLabel(snapshot?.data.don_vi_tinh) || ""}`],
                  ["Tên mặt hàng", snapshot?.data.ten_mat_hang],
                  ["Mã nội bộ", snapshot?.data.ma_mat_hang],
                  ["Đơn vị tính", unitLabel(snapshot?.data.don_vi_tinh)],
                  ["Cập nhật tồn", dateTime(snapshot?.data.ton_kho_updated_at)],
                ]}
              />
            ) : (
              <ItemForm snapshot={snapshot} />
            )
          }
        </RecordPanel>
      </div>
    </>
  );
}
function ItemForm({ snapshot }) {
  const record = snapshot?.data;
  const navigate = useNavigate();
  const { confirm, notify } = useFeedback();
  const action = useWrite();
  const { save, busy, error } = useSave();
  const catalog = useCatalog();
  const [search] = useSearchParams();
  const [lines, setLines] = useState([newLine()]);
  const [values, setValues] = useState({
    ten_mat_hang: record?.ten_mat_hang || "",
    sku: record?.sku || "",
    loai_mat_hang:
      record?.loai_mat_hang ||
      (search.get("loai_mat_hang") === "thanh_pham" ? "thanh_pham" : "linh_kien"),
    don_vi_tinh: record?.don_vi_tinh || "cai",
    mau_sac: record?.mau_sac || "",
    mo_ta: record?.mo_ta || "",
    don_gia: record?.don_gia ?? "",
  });
  const field = (name) => ({
    value: values[name],
    onChange: (event) => setValues({ ...values, [name]: event.target.value }),
  });
  function submit(event) {
    event.preventDefault();
    const body = itemPayload(values, { record, lines });
    save(
      {
        path: record ? `${API.items}/${record.id}` : API.items,
        method: record ? "patch" : "post",
        body,
        etag: snapshot?.etag,
        versioned: Boolean(record),
      },
      (result) => navigate(`/kho/mat-hang/${result.data.id}`),
    );
  }
  return (
    <form className="stack" onSubmit={submit}>
      <ErrorNotice error={error} />
      <div className="form-grid">
        <Field label="SKU" required {...field("sku")} />
        <Field label="Tên mặt hàng" required {...field("ten_mat_hang")} />
        <Field
          as="select"
          label="Loại mặt hàng"
          required
          options={warehouseTypes.slice(1)}
          disabled={Boolean(record)}
          {...field("loai_mat_hang")}
        />
        <Field
          as="select"
          label="Đơn vị tính"
          required
          options={itemUnitOptions(record?.don_vi_tinh)}
          {...field("don_vi_tinh")}
        />
        <Field
          label="Màu sắc"
          pattern="[a-z]+(_[a-z]+)*"
          placeholder="den, trang…"
          {...field("mau_sac")}
        />
        <Field
          label="Đơn giá (VND)"
          required
          type="number"
          min="0"
          max={Number.MAX_SAFE_INTEGER}
          step="1"
          {...field("don_gia")}
        />
      </div>
      {!record && values.loai_mat_hang === "thanh_pham" && (
        <QueryState query={catalog}>
          <h3>Định mức đầu tiên cho một thành phẩm</h3>
          <DocumentLines
            lines={lines}
            onChange={setLines}
            items={catalog.data?.data || []}
            types={["linh_kien"]}
          />
        </QueryState>
      )}
      <Field as="textarea" label="Mô tả" rows={3} {...field("mo_ta")} />
      {record && (
        <>
          <div className="warehouse-stock-summary">
            {[
              ["Tồn thực tế", record.so_luong_ton],
              ["Đang giữ", record.so_luong_dang_giu],
              ["Còn dùng", record.so_luong_con_dung],
            ].map(([label, value]) => (
              <div key={label}>
                <span className="muted">{label}</span>
                <strong>
                  {number(value)} <small>{unitLabel(record.don_vi_tinh)}</small>
                </strong>
              </div>
            ))}
          </div>
        </>
      )}
      <div className="actions actions-end">
        {record?.loai_mat_hang === "thanh_pham" && (
          <Button
            variant={record.is_active ? "danger" : "secondary"}
            onClick={() =>
              confirm({
                title: record.is_active ? "Ngừng sử dụng mặt hàng" : "Dùng lại thành phẩm",
                description: `${record.ma_mat_hang} · ${record.ten_mat_hang}. Mặt hàng ngừng hoạt động không được dùng trong chứng từ mới.`,
                impact: record.is_active
                  ? "Giữ nguyên mặt hàng, số dư tồn và chứng từ cũ. Các yêu cầu đã gửi vẫn tiếp tục được xử lý."
                  : "Backend kiểm tra và dùng lại công thức ngừng gần nhất; không thay đổi tồn kho.",
                danger: record.is_active,
                onConfirm: async () => {
                  await action.mutateAsync({
                    path: `${API.items}/${record.id}`,
                    method: record.is_active ? "delete" : "patch",
                    body: record.is_active ? null : { is_active: true },
                    etag: snapshot.etag,
                  });
                  notify(
                    record.is_active ? "Đã ngừng sử dụng mặt hàng." : "Đã dùng lại thành phẩm.",
                  );
                },
              })
            }
          >
            {record.is_active ? "Ngừng sử dụng…" : "Dùng lại thành phẩm"}
          </Button>
        )}
        <Button
          type="submit"
          disabled={
            busy || (!record && values.loai_mat_hang === "thanh_pham" && !catalog.isSuccess)
          }
        >
          {busy ? "Đang lưu…" : "Lưu"}
        </Button>
      </div>
    </form>
  );
}
